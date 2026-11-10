"""Production conversation and FrameX reasoning with controlled language responses."""
from __future__ import annotations

import json

import pytest

from eval.contracts import SystemInput
from eval.metrics import invariants
from eval.runner import run_cases
from pipeline.eval_adapter import EvaluationModel, RefundSystemAdapter
from pipeline.llm import ModelAnswer, ModelCallFailed
from pipeline.slots import EXTRACT_PROMPT
from tests.test_pipeline import FULL, LATE, MESSAGE, ScriptedModel, workspace  # noqa: F401


def case(messages=None, **request):
    return SystemInput("opaque", request, messages or [{"role": "user", "content": MESSAGE}], {})


def adapter(knowledge, slots=None, **kwargs):
    return RefundSystemAdapter(knowledge, model_factory=lambda: ScriptedModel(slots=slots), **kwargs)


def test_production_conversation_has_real_bindings_and_ordered_audit(workspace):
    kb = workspace(LATE)
    slots = {**FULL, "price": {"chf": 40, "quote": "40"}}
    system = adapter(kb, [slots])
    observed = system.run(case([{"role": "user", "content": MESSAGE + " CHF 40"}], board_event="not_model_input"))
    assert observed.decision == "refund"
    assert observed.facts["refundCHF"] == "10.00"
    assert observed.facts["refundStatus"] == "entitled"
    assert isinstance(observed.facts["actualArrival"], int)
    assert set(invariants(observed).values()) == {"passed"}
    assert [e["name"] for e in observed.events if e["kind"] == "execute"] == ["offers", "verdict"]
    assert "not_model_input" not in json.dumps(observed.metadata)
    assert len(observed.metadata["transcript"]) == 2
    # Every attempt gets a clean case and receipt, including after a terminal result.
    repeated = system.run(case([{"role": "user", "content": MESSAGE + " CHF 40"}]))
    assert repeated.facts == observed.facts
    assert repeated.metadata["receipt_id"] != observed.metadata["receipt_id"]


def test_price_is_asked_once_and_second_turn_finishes(workspace):
    system = adapter(workspace(LATE), [FULL, {"price": {"chf": 40, "quote": "40"}}])
    observed = system.run(case([{"role": "user", "content": MESSAGE},
                                {"role": "assistant", "content": "What was the price?"},
                                {"role": "user", "content": "CHF 40"}]))
    assert observed.decision == "refund"
    assert observed.facts["refundCHF"] == "10.00"
    assert len([e for e in observed.events if e["kind"] == "ask" and e["slot"] == "price"]) == 1
    assert any(e.get("message_index") == 2 for e in observed.events if e.get("slot") == "price")
    assert observed.metadata["transcript"][2]["generated"] is False
    assert set(invariants(observed).values()) == {"passed"}


def test_fabricated_quotes_are_rejected_and_repaired_once(workspace):
    bad = {"origin": {"station": "Aarau", "quote": "imaginary words"}}
    observed = adapter(workspace(LATE), [bad, bad]).run(case())
    assert observed.decision == "question"
    assert observed.facts["critiqueReason"] == "quote_not_found"
    assert len([e for e in observed.events if e["kind"] == "repair" and e["scope_id"].endswith(":slots")]) == 1
    assert not [e for e in observed.events if e["kind"] == "slot" and e.get("accepted")]
    assert invariants(observed)["checked_execution"] == "unverified"


def test_contextual_question_records_missing_slots_and_phrasing_repair(workspace):
    def model_factory():
        model = ScriptedModel(slots=[{}])
        model.question = "You will receive 50 CHF."
        return model

    system = RefundSystemAdapter(workspace(LATE), model_factory=model_factory)
    observed = system.run(case())
    assert observed.decision == "question"
    assert observed.facts["critiqueReason"] == "missing_slot"
    assert {e["slot"] for e in observed.events if e["kind"] == "ask"} == {
        "origin", "destination", "date", "time",
    }
    repairs = [e for e in observed.events if e["kind"] == "repair" and ":phrasing:" in e["scope_id"]]
    assert len(repairs) == 1
    assert "50" not in observed.reply


def test_engine_failure_remains_a_sanitized_technical_error(workspace):
    observed = adapter(workspace(LATE), [FULL]).run(case(fault="tool_timeout"))
    assert observed.decision == "error"
    assert observed.error == "TimeoutError"
    assert observed.facts["refundPercent"] is None
    assert "injected" not in observed.reply
    assert any(e["kind"] == "execute" for e in observed.events)


def test_correction_is_checked_again_before_selecting_a_train(workspace):
    kb = workspace(LATE, ("via", [("sp_1", "08:05", "08:05"), ("sp_3", "09:00", "09:00")]))
    corrected = {**FULL, "destination": {"station": "Olten", "quote": "Olten"}}
    observed = adapter(kb, [FULL, corrected]).run(case([
        {"role": "user", "content": MESSAGE},
        {"role": "assistant", "content": "Is Zürich HB correct?"},
        {"role": "user", "content": "Actually I meant Olten instead."}],
        fault="several_departures_after_correction"))
    assert observed.decision == "question"
    assert observed.facts["destination"] == "sp_3"
    assert observed.facts["critiqueReason"] == "several_departures"
    assert "Olten" in observed.reply


def test_snapshot_hash_mismatch_is_rejected_before_model_calls(workspace):
    system = adapter(workspace(LATE))
    request = case()
    request.snapshot["rules.fx"] = "wrong"
    with pytest.raises(ValueError, match="snapshot"):
        system.run(request)


def test_replay_mode_cannot_fall_through_to_a_paid_call(tmp_path, monkeypatch):
    model = EvaluationModel(tmp_path, mode="replay")
    monkeypatch.setattr(model, "_openai", lambda: pytest.fail("unexpected API call"))
    with pytest.raises(ModelCallFailed, match="unavailable"):
        model.ask_json(EXTRACT_PROMPT, "no recording")


def test_recorded_calls_are_excluded_from_performance_aggregates(workspace):
    from eval.contracts import Case
    from pipeline.llm import LanguageModel

    class RecordedModel(LanguageModel):
        def __init__(self):
            self.calls = [{"mode": "replay", "stage": "extraction", "elapsed_ms": 1, "usage": {}}]

        def ask_json(self, system, user, *, effort="low"):
            data = {} if system == EXTRACT_PROMPT else {"decision": "question", "reply": "From where?"}
            return ModelAnswer(data, json.dumps(data), "replay", "now", 0.0)

    system = RefundSystemAdapter(workspace(LATE), model_factory=RecordedModel)
    report = run_cases(system, [Case("recorded", {}, {"decision": "question"},
                                         messages=[{"role": "user", "content": "Help"}])])
    assert report["summary"]["latency"]["count"] == 0
    assert report["summary"]["stages"] == {}
    assert report["rows"][0]["latency_ms"] is not None


@pytest.mark.parametrize("price, amount, paid", [(1999, 500, False), (2000, 500, True), (2002, 501, True)])
def test_exact_payout_and_half_up_display_through_real_assistant(workspace, price, amount, paid):
    text = MESSAGE + f" CHF {price / 100:.2f}"
    slots = {**FULL, "price": {"chf": price / 100, "quote": f"{price / 100:.2f}"}}
    observed = adapter(workspace(LATE), [slots]).run(case([{"role": "user", "content": text}]))
    assert observed.facts["refundCHF"] == f"{amount / 100:.2f}"
    assert observed.facts["paidOut"] is paid
    assert observed.decision == ("refund" if paid else "no_refund")


def test_faster_transfer_is_considered_even_when_the_train_continues_directly(workspace):
    from tests.test_pipeline import CASE, only
    kb = workspace(("slow", [("sp_1", "08:00", "08:00"), ("sp_3", "08:30", "08:30"),
                              ("sp_2", "10:00", "10:00")]),
                   ("fast", [("sp_3", "08:35", "08:35"), ("sp_2", "09:00", "09:00")]))
    offered = only(kb)
    verdict = kb.verdict(CASE, offered, 4000)
    assert offered.changes == 1
    assert verdict.planned_arrival == "09:00"
    assert verdict.delay_minutes == 0


@pytest.mark.parametrize("fault, decision", [("model_timeout", "error"),
                                              ("fabricated_quote_after_repair", "question"),
                                              ("repair_exhausted", "question")])
def test_declared_model_faults_exercise_production_checks(workspace, tmp_path, fault, decision):
    class Controlled(EvaluationModel):
        def _openai(self):
            pytest.fail("fault extraction and replay fallback must not call the provider")

    system = RefundSystemAdapter(workspace(LATE), model_factory=lambda: Controlled(tmp_path, mode="replay", fault=fault))
    observed = system.run(case(fault=fault))
    assert observed.decision == decision
    assert observed.facts["refundPercent"] is None
    if decision == "error":
        assert observed.error == "ModelCallFailed"
    else:
        repairs = [e for e in observed.events if e["kind"] == "repair" and e["scope_id"].endswith(":slots")]
        assert len(repairs) == 1
        assert not any(e.get("accepted") for e in observed.events if e["kind"] == "slot")


def test_new_journey_keeps_original_message_provenance(workspace):
    full = {**FULL, "price": {"chf": 40, "quote": "40"}}
    system = adapter(workspace(LATE), [full, full])
    observed = system.run(case([{"role": "user", "content": MESSAGE + " CHF 40"},
                                {"role": "assistant", "content": "Thank you."},
                                {"role": "user", "content": MESSAGE + " CHF 40 again"}]))
    assert observed.decision == "refund"
    slot_events = [e for e in observed.events if e["kind"] == "slot" and e.get("accepted")]
    assert {e["message_index"] for e in slot_events} == {0, 2}


def test_scripted_context_reaches_extraction_but_is_not_passenger_evidence(workspace):
    captured = []

    class ContextModel(ScriptedModel):
        def ask_json(self, system, user, *, effort="low"):
            if system == EXTRACT_PROMPT:
                captured.append(json.loads(user))
            return super().ask_json(system, user, effort=effort)

    bad = {"origin": {"station": "Aarau", "quote": "Aarau"}}
    system = RefundSystemAdapter(workspace(LATE), model_factory=lambda: ContextModel([bad, bad]))
    observed = system.run(case([{"role": "assistant", "content": "Did you leave from Aarau?"},
                                {"role": "user", "content": "Please check my refund."}]))
    assert captured[0]["context"] == [{"role": "assistant", "content": "Did you leave from Aarau?"}]
    assert observed.decision == "question"
    assert observed.facts["critiqueReason"] == "quote_not_found"
    assert not any(e.get("accepted") for e in observed.events if e["kind"] == "slot")
