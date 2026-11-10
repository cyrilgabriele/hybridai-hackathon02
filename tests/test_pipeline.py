"""The refund chat on a small generated workspace: real rules, scripted model."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from openai.types.shared import ReasoningEffort

from ontology import service
from pipeline.assistant import Assistant, match_offer
from pipeline.handoff import Desk
from pipeline.knowledge import Case, Knowledge, Offer
from pipeline.llm import LanguageModel, ModelAnswer, ModelCallFailed
from pipeline.reply import (
    ASK_PROMPT,
    OUTCOMES,
    PHRASE_PROMPT,
    PLACEHOLDER,
    ask,
    critique,
    say,
)
from pipeline.slots import EXTRACT_PROMPT
from pipeline.slots import critique as critique_slots
from pipeline.state import Conversation

FX = Path(__file__).resolve().parents[1] / "fx"
DAY = "2026-11-07"
AAU, ZUE, VIA = "sp_1", "sp_2", "sp_3"
ZUE_B = "sp_4"
NAMES = {AAU: "Aarau", ZUE: "Zürich HB", VIA: "Olten", ZUE_B: "Zürich Oerlikon"}


def epoch(clock: str) -> int:
    value = service.timestamp(f"{DAY}T{clock}:00")
    assert value is not None
    return value


def trip_id(name: str) -> str:
    return "trip_" + hashlib.md5(name.encode()).hexdigest()


def stops_block(name: str, stops: list[tuple]) -> list[str]:
    """Facts of one dated trip; each stop is (station, planned, actual, flags)."""
    trip = trip_id(name)
    segment = f"segment_{trip[5:]}"
    lines = [f"{trip}:Trip.", f'{trip}[tripRef -> "{name}"].', f'{trip}[observedOn -> "{DAY}"].',
             f'{trip}[serviceCategory -> "IC"].', f'{trip}[lineText -> "{name.upper()}"].',
             f"{segment}:RideSegment.", f"{segment}[ofTrip -> {trip}]."]
    for sequence, (station, planned, actual, *flags) in enumerate(stops, 1):
        event = "ev_" + hashlib.md5(f"{name}{sequence}".encode()).hexdigest()
        cancelled = "cancelled" in flags
        lines += [f"{event}:StopEvent.", f"{event}[ofTrip -> {trip}].", f"{event}[atStopPoint -> {station}].",
                  f"{event}[stopSequence -> {sequence}].", f"{event}[cancelled -> {str(cancelled).lower()}].",
                  f"{event}[passThrough -> false].", f"{event}[scheduledArrivalEpoch -> {epoch(planned)}].",
                  f"{event}[scheduledDepartureEpoch -> {epoch(planned)}].", f"{event}[rideSegment -> {segment}]."]
        if actual is not None and not cancelled:
            lines += [f"{event}[arrivalEpoch -> {epoch(actual)}].", f"{event}[departureEpoch -> {epoch(actual)}]."]
    return lines


@pytest.fixture
def workspace(tmp_path: Path):
    def build(*trips: tuple[str, list[tuple]]) -> Knowledge:
        for rule in FX.glob("*.fx"):
            if rule.name[:2] < "60":
                shutil.copy(rule, tmp_path / rule.name)
        spine = [f"{sid}[designation -> \"{name}\"]." for sid, name in NAMES.items()]
        (tmp_path / "60-spine.fx").write_text("\n".join(spine), encoding="utf-8")
        lines = [line for trip, stops in trips for line in stops_block(trip, stops)]
        (tmp_path / "70-ist-daten-sbb.fx").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return Knowledge(tmp_path)
    return build


CASE = Case(AAU, "Aarau", ZUE, "Zürich HB", DAY, "08:00")
LATE = ("ic", [(AAU, "08:00", "08:00"), (ZUE, "09:00", "10:05")])


def only(kb: Knowledge) -> Offer:
    offers = kb.offers(CASE).offers
    assert len(offers) == 1
    return offers[0]


# --- rules through per-case worlds -------------------------------------------

def test_a_late_train_earns_the_rule_share(workspace):
    kb = workspace(LATE)
    verdict = kb.verdict(CASE, only(kb), None)
    assert (verdict.decision, verdict.outcome, verdict.delay_minutes, verdict.percent) == ("refund", "refund_percent", 65, 25)
    assert verdict.proof


def test_the_named_price_gives_an_amount(workspace):
    kb = workspace(LATE)
    verdict = kb.verdict(CASE, only(kb), 4000)
    assert (verdict.outcome, verdict.refund_rappen) == ("refund_amount", 1000)


def test_an_amount_below_the_minimum_is_not_paid(workspace):
    kb = workspace(LATE)
    verdict = kb.verdict(CASE, only(kb), 1000)
    assert (verdict.decision, verdict.outcome, verdict.refund_rappen) == ("no_refund", "below_minimum", 250)


def test_an_unrecorded_arrival_is_handed_on_with_the_rules_reason(workspace):
    kb = workspace(("ic", [(AAU, "08:00", "08:00"), (ZUE, "09:00", None)]))
    verdict = kb.verdict(CASE, only(kb), None)
    assert verdict.decision == "handoff"
    assert verdict.percent is None
    assert "no actual arrival" in verdict.reason or "no recorded actual time" in verdict.reason
    assert verdict.assessment and verdict.assessment["prompt"]


def test_a_day_outside_the_data_is_not_checkable(workspace):
    kb = workspace(LATE)
    result = kb.offers(Case(AAU, "Aarau", ZUE, "Zürich HB", "2026-11-08", "08:00"))
    assert result.not_checkable == "journeys on this day are not in the SBB data"
    assert result.offers == []


def test_a_train_that_arrives_before_it_departs_is_not_offered(workspace):
    phantom = ("merged", [(AAU, "08:10", "08:10"), (ZUE, "08:05", None, "cancelled")])
    real = ("ic", [(AAU, "08:20", "08:20"), (ZUE, "09:00", "09:01")])
    offers = workspace(phantom, real).offers(CASE).offers
    assert [offer.departure for offer in offers] == ["08:20"]


def test_a_change_needs_both_trains_in_the_world(workspace):
    first = ("a", [(AAU, "08:00", "08:00"), (VIA, "08:30", "08:45")])
    missed = ("b", [(VIA, "08:40", "08:40"), (ZUE, "09:10", "09:10")])
    taken = ("c", [(VIA, "09:40", "09:40"), (ZUE, "10:10", "10:10")])
    unrelated = ("d", [(ZUE_B, "08:30", "08:30"), (ZUE, "12:30", "12:30")])
    kb = workspace(first, missed, taken, unrelated)
    selected = set(kb.select_trips(AAU, ZUE, epoch("07:30"), epoch("08:30")))
    assert {trip_id("a"), trip_id("b"), trip_id("c")} <= selected
    verdict = kb.verdict(CASE, only(kb), None)
    assert (verdict.delay_minutes, verdict.percent) == (60, 25)


# --- host checks -------------------------------------------------------------

def reply(**slots) -> dict:
    return {"origin": None, "destination": None, "date": None, "time": None, "price": None, "train": None,
            "language": "en", **slots}


def reasons(kb, data, message):
    _, problems = critique_slots(data, message, kb)
    return {problem.slot: problem.reason for problem in problems}


def test_a_quote_not_in_the_message_is_refused(workspace):
    kb = workspace(LATE)
    data = reply(origin={"station": "Aarau", "quote": "Basel"})
    assert reasons(kb, data, "from Aarau") == {"origin": "quote_not_found"}


def test_an_unknown_station_is_refused(workspace):
    kb = workspace(LATE)
    data = reply(origin={"station": "Atlantis", "quote": "Atlantis"})
    assert reasons(kb, data, "from Atlantis") == {"origin": "unknown_station"}


def test_a_bare_city_is_never_resolved_by_the_model(workspace):
    kb = workspace(LATE, ("x", [(ZUE_B, "08:00", "08:00"), (AAU, "09:00", "09:00")]))
    data = reply(destination={"station": "Zürich HB", "quote": "to Zürich"})
    reading, _ = critique_slots(data, "to Zürich", kb)
    assert "destination" not in reading.accepted
    assert reading.ambiguous["destination"][1] == ["Zürich HB", "Zürich Oerlikon"]


def test_a_time_the_quote_does_not_say_is_refused(workspace):
    kb = workspace(LATE)
    data = reply(time={"value": "14:30", "quote": "at 8"})
    assert reasons(kb, data, "at 8") == {"time": "value_not_in_quote"}


def test_the_passengers_train_is_matched_by_number_time_or_name():
    offers = [Offer("t1", "IR13", "07:37", "08:52", 0, ("a",)), Offer("t2", "IC 5", "07:58", "08:58", 0, ("b",))]
    assert match_offer("2", offers) == offers[1]
    assert match_offer("the 7.37 one", offers) == offers[0]
    assert match_offer("I took IC 5", offers) == offers[1]
    assert match_offer("no idea", offers) is None


# --- replies -----------------------------------------------------------------

VALUES = {"origin": "Aarau", "destination": "Zürich HB", "delay": "65 minutes", "percent": "25", "minimum_chf": "CHF 5"}
GOOD = "Your train from {origin} reached {destination} {delay} late. You get {percent} % back. Under {minimum_chf} nothing is paid. What did it cost?"


def check(text: str, decision: str = "refund") -> list[str]:
    return critique({"decision": decision, "reply": text}, OUTCOMES["refund_percent"], VALUES, None)


def test_a_clean_reply_passes():
    assert check(GOOD) == []


@pytest.mark.parametrize(("text", "decision", "problem"), [
    (GOOD.replace("{delay}", "65 minutes"), "refund", "digit_outside_placeholder"),
    (GOOD, "no_refund", "wrong_decision"),
    (GOOD.replace("{percent}", "{share}"), "refund", "unknown_placeholder"),
    (GOOD.replace("{percent}", "{the refund share}"), "refund", "unknown_placeholder"),
    (GOOD.replace("{destination}", "the station"), "refund", "missing_placeholder"),
    (GOOD + " It also left on time. Have a nice day.", "refund", "too_long"),
])
def test_a_reply_that_states_a_fact_itself_is_refused(text, decision, problem):
    assert any(found.startswith(problem) for found in check(text, decision))


class ScriptedModel(LanguageModel):
    """Stands in for GPT-5 mini: canned slots, well-behaved or misbehaving phrasing."""

    def __init__(self, slots: list[dict] | None = None, phrase_ok: bool = True, fail: bool = False):
        self.slots = list(slots or [])
        self.phrase_ok = phrase_ok
        self.fail = fail
        self.phrased: list[dict] = []
        self.asked: list[dict] = []
        self.question = "Sorry about that. On {date}, from where to where did you travel?"

    def ask_json(self, system: str, user: str, *, effort: ReasoningEffort = "low") -> ModelAnswer:
        if self.fail:
            raise ModelCallFailed("APIConnectionError")
        if system == EXTRACT_PROMPT:
            data = self.slots.pop(0) if self.slots else reply()
        elif system == PHRASE_PROMPT:
            request = json.loads(user)
            self.phrased.append(request)
            names = " ".join("{" + name + "}" for name in request["required"])
            data = {"decision": request["decision"], "reply": names if self.phrase_ok else "65 minutes, sorry."}
        elif system == ASK_PROMPT:
            self.asked.append(json.loads(user))
            data = {"decision": "question", "reply": self.question}
        else:
            data = {"verdict": "unclear", "reason": "the record is incomplete"}
        return ModelAnswer(data, json.dumps(data), "live", "now", 0.0)


def assistant(kb: Knowledge, model: ScriptedModel) -> Assistant:
    return Assistant(kb, model, Desk())


FULL = reply(origin={"station": "Aarau", "quote": "Aarau"}, destination={"station": "Zürich HB", "quote": "Zürich HB"},
             date={"value": DAY, "quote": "7 November"}, time={"value": "08:00", "quote": "8"})
MESSAGE = "Aarau to Zürich HB on 7 November at 8"


def test_the_model_never_receives_a_value(workspace):
    model = ScriptedModel([FULL])
    conv = Conversation()
    text = assistant(workspace(LATE), model).handle(conv, MESSAGE)
    assert "65" in text and "25" in text
    assert model.phrased
    assert not any("65" in json.dumps(request) for request in model.phrased)


def test_a_misbehaving_reply_falls_back_to_rule_written_words(workspace):
    conv = Conversation()
    text = assistant(workspace(LATE), ScriptedModel([FULL], phrase_ok=False)).handle(conv, MESSAGE)
    assert "65 minutes late" in text and "25 %" in text
    assert any(step.status == "refused" for step in conv.trace)


def test_everything_missing_is_asked_for_with_the_conversation_as_context(workspace):
    partial = reply(date={"value": DAY, "quote": "7 November"})
    model = ScriptedModel([partial])
    conv = Conversation()
    text = assistant(workspace(LATE), model).handle(conv, "On 7 November my train was late")
    request = model.asked[-1]
    assert request["conversation"] == ["On 7 November my train was late"]
    assert list(request["known"]) == ["{date}"]
    assert len(request["missing"]) == 3
    assert text == "Sorry about that. On 07.11.2026, from where to where did you travel?"
    assert conv.asked_for == "origin, destination, time"


@pytest.mark.parametrize("question", [
    "Which station did you leave on the 7th?",
    "Tell me your station.",
    "You will receive money. Where did you start?",
])
def test_a_question_that_states_a_fact_or_asks_nothing_falls_back_to_fixed_words(workspace, question):
    partial = reply(date={"value": DAY, "quote": "7 November"})
    model = ScriptedModel([partial])
    model.question = question
    conv = Conversation()
    text = assistant(workspace(LATE), model).handle(conv, "On 7 November my train was late")
    assert text == " ".join(OUTCOMES[f"ask_{slot}"].en for slot in ("origin", "destination", "time"))
    assert any(step.status == "refused" for step in conv.trace)


def test_a_failed_question_call_still_asks_with_fixed_words():
    class Down(ScriptedModel):
        def ask_json(self, system: str, user: str, *, effort: ReasoningEffort = "low") -> ModelAnswer:
            raise ModelCallFailed("Timeout")

    trace = []
    text = ask(Down(), ["date"], ["my train was late"], {}, "de", trace)
    assert text == OUTCOMES["ask_date"].de
    assert trace[0].status == "failed"


def test_a_technical_failure_says_so_and_gives_no_verdict(workspace):
    conv = Conversation()
    text = assistant(workspace(LATE), ScriptedModel(fail=True)).handle(conv, MESSAGE)
    assert text == "Something went wrong. Please try again."
    assert conv.trace[-1].status == "failed"
    assert conv.messages == []


def test_a_person_decides_and_the_answer_reaches_the_passenger_once(workspace):
    unmeasured = ("ic", [(AAU, "08:00", "08:00"), (ZUE, "09:00", None)])
    bot = assistant(workspace(unmeasured), ScriptedModel([FULL]))
    conv = Conversation()
    text = bot.handle(conv, MESSAGE)
    assert conv.stage == "handed_over"
    assert conv.handoff_id is not None and conv.handoff_id in text
    case = bot.desk.get(conv.handoff_id)
    assert case is not None and case.note == "the record is incomplete"
    assert bot.deliver(conv) is None
    bot.desk.decide(case.id, "refund", 30, "Goodwill.")
    message = bot.deliver(conv)
    assert message is not None and "30 %" in message and "Goodwill." in message
    assert bot.deliver(conv) is None


def test_phrasing_failure_still_answers_with_fixed_words(workspace):
    class Flaky(ScriptedModel):
        def ask_json(self, system: str, user: str, *, effort: ReasoningEffort = "low") -> ModelAnswer:
            if system == PHRASE_PROMPT:
                raise ModelCallFailed("Timeout")
            return super().ask_json(system, user, effort=effort)

    trace = []
    text = say(Flaky(), "ask_date", {}, "de", trace)
    assert text == OUTCOMES["ask_date"].de
    assert trace[0].status == "failed"


def test_official_words_are_accepted_whatever_the_model_answers(workspace):
    kb = workspace(LATE)
    data = reply(origin={"station": "Aarau Hauptbahnhof", "quote": "Aarau"})
    reading, problems = critique_slots(data, "from Aarau", kb)
    assert not problems and reading.accepted["origin"].station_id == AAU


def test_every_outcome_has_the_same_values_in_both_languages():
    for outcome in OUTCOMES.values():
        assert set(PLACEHOLDER.findall(outcome.en)) == set(PLACEHOLDER.findall(outcome.de))
