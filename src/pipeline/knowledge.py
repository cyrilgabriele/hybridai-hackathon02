"""What one refund decision reads from the knowledge base.

Adding a case to one long-lived session of the full workspace makes the engine
recompute everything, and the refund rules read their cases under NOT and
aggregates, so the cost grows with every case. Each decision therefore gets its
own small world: the unchanged rule files of `fx/` plus only the source facts
those rules can use, namely trips at the origin in the case's window, and trips
at the destination that a change from one of them could reach. This module is
the only place that writes FrameX source for a case; it does so from validated
identifiers, never from model text. See docs/adrs/0001_refund_case_worlds.md.
"""

from __future__ import annotations

import importlib.resources
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from framex import FrameXError

from ontology import service
from runtime.client import Client
from runtime.query import binary
from runtime.session import LIMITS

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "fx"
GATE = Path(__file__).resolve().parent / "programs" / "competence_gate.fx"
WINDOW_SECONDS = 30 * 60
TRANSFER_SECONDS = 300
MAX_RESPONSE_BYTES = 256 * 1024 * 1024
REQUEST_TIMEOUT = 300.0
PROOF_LINES = 90
ZONE = ZoneInfo("Europe/Zurich")

_TRIP = re.compile(r"^(trip_[0-9a-f]+):Trip\.$")
_FIELD = re.compile(
    r"^(ev_[0-9a-f]+)\[(atStopPoint|stopSequence|scheduledDepartureEpoch|scheduledArrivalEpoch|"
    r"departureEpoch|arrivalEpoch) -> ([^\]]+)\]\.$"
)
_DESIGNATION = re.compile(r'^(sp_\d+)\[designation -> "(.*)"\]\.$')
_STOP = re.compile(r"\[atStopPoint -> (sp_\d+)\]")
_SEARCH = re.compile(r"refundSearch\[maxChangeWait -> (\d+); maxStartWait -> (\d+); maxJourney -> (\d+)\]")
_ASSESS_PROMPT = re.compile(r'assessPrompt:Prompt\[text -> (".*")\]\.')


def fold(text: str) -> str:
    """Compare names without case, accents or punctuation; no aliases."""
    plain = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch)).casefold()
    return " ".join(re.sub(r"[^\w ]", " ", plain).split())


def clock(epoch: int | None) -> str:
    return "" if epoch is None else datetime.fromtimestamp(epoch, ZONE).strftime("%H:%M")


def _decode(value):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _literal(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _chunks(lines: list[str], limit: int = 200_000):
    batch: list[str] = []
    size = 0
    for line in lines:
        batch.append(line)
        size += len(line) + 1
        if size >= limit:
            yield "\n".join(batch)
            batch, size = [], 0
    if batch:
        yield "\n".join(batch)


@dataclass(slots=True)
class _Event:
    stop: str = ""
    sequence: int = 0
    times: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class Case:
    """A journey whose every field has passed the host's checks."""

    origin_id: str
    origin_name: str
    destination_id: str
    destination_name: str
    day: str
    time: str


@dataclass(frozen=True)
class Offer:
    """One departure the rules offer; `boards` can hold twin events in the data."""

    id: str
    label: str
    departure: str
    arrival: str
    changes: int
    boards: tuple[str, ...]

    def line(self, language: str = "en") -> str:
        arrives, change = {"de": ("Ankunft", "Umstieg"), "fr": ("arrivée", "correspondance"),
                           "it": ("arrivo", "cambio")}.get(language, ("arrives", "change"))
        text = f"{self.departure} {self.label}, {arrives} {self.arrival}"
        return f"{text}, {self.changes} {change}" if self.changes else text


@dataclass
class OfferResult:
    offers: list[Offer]
    not_checkable: str | None
    asserted: str
    trips: int
    seconds: float


@dataclass
class Verdict:
    decision: str  # refund | no_refund | handoff
    outcome: str  # key of pipeline.reply.OUTCOMES
    reason: str = ""
    delay_minutes: int | None = None
    percent: int | None = None
    refund_rappen: int | None = None
    planned_arrival: str = ""
    actual_arrival: str = ""
    cancelled: bool = False
    threshold_minutes: int | None = None
    minimum_rappen: int | None = None
    proof: str = ""
    asserted: str = ""
    assessment: dict | None = None
    trips: int = 0
    seconds: float = 0.0


class World:
    """One running engine holding one decision's rules and facts."""

    def __init__(self, rules: str, facts: list[str]):
        self.client = Client(
            binary(), retain_transcript=False, max_response_bytes=MAX_RESPONSE_BYTES, request_timeout=REQUEST_TIMEOUT,
        )
        try:
            self.client.load_begin(**LIMITS)
            self.client.load_chunk(rules, file="rules.fx")
            for piece in _chunks(facts):
                self.client.load_chunk(piece, file="case.fx")
            self.client.load_commit()
        except BaseException:
            self.client.close()
            raise

    def rows(self, query: str) -> list[dict]:
        return self.client.query(query).get("bindings", [])

    def value(self, subject: str, slot: str):
        found = self.rows(f"?- {subject}[{slot} -> ?V].")
        return _decode(found[0]["V"]) if found else None

    def proof(self, fact: str) -> str:
        """The first lines only: an aggregate's whole proof can exceed 50 MB."""
        try:
            text = str(self.client.explain(fact))
        except (FrameXError, RuntimeError, TimeoutError, ValueError) as exc:  # display only; say why it is missing
            return f"(no proof shown: {type(exc).__name__})"
        return "\n".join(text.splitlines()[:PROOF_LINES])

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()


class Knowledge:
    """The workspace indexed once. It holds no engine; worlds are made per decision."""

    def __init__(self, workspace: Path = WORKSPACE):
        self.workspace = workspace
        self.blocks: dict[str, list[str]] = {}
        self.events: dict[str, list[_Event]] = {}
        self.trips_at: dict[str, set[str]] = {}
        self.names: dict[str, str] = {}
        self.ids_by_name: dict[str, list[str]] = {}
        self._index_stations()
        self._index_service()
        self.rules = self._rules()
        self._by_fold: dict[str, list[str]] = {}
        for name in self.ids_by_name:
            self._by_fold.setdefault(fold(name), []).append(name)
        found = _SEARCH.search(self.rules)
        prompt = _ASSESS_PROMPT.search(self.rules)
        if found is None or prompt is None:
            raise ValueError("refundSearch bounds or assessPrompt not found in the rule files")
        self.max_change_wait, self.max_start_wait, self.max_journey = map(int, found.groups())
        self.assess_prompt: str = _decode(prompt.group(1))

    # --- indexing ---------------------------------------------------------

    def _index_stations(self) -> None:
        with open(self.workspace / "60-spine.fx", encoding="utf-8") as handle:
            for raw in handle:
                match = _DESIGNATION.match(raw.rstrip("\n"))
                if match:
                    self.names[match.group(1)] = match.group(2)
                    self.ids_by_name.setdefault(match.group(2), []).append(match.group(1))

    def _index_service(self) -> None:
        current = None
        partial: dict[str, _Event] = {}
        with open(self.workspace / "70-ist-daten-sbb.fx", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                match = _TRIP.match(line)
                if match:
                    self._close_trip(current, partial)
                    current, partial = match.group(1), {}
                    self.blocks[current] = []
                if current is None or not line or line.startswith("//"):
                    continue
                self.blocks[current].append(line)
                found = _FIELD.match(line)
                if found:
                    event = partial.setdefault(found.group(1), _Event())
                    if found.group(2) == "atStopPoint":
                        event.stop = found.group(3)
                    elif found.group(2) == "stopSequence":
                        event.sequence = int(found.group(3))
                    else:
                        event.times.append(int(found.group(3)))
        self._close_trip(current, partial)

    def _close_trip(self, trip: str | None, partial: dict[str, _Event]) -> None:
        if trip is None:
            return
        self.events[trip] = sorted(partial.values(), key=lambda event: event.sequence)
        for event in partial.values():
            if event.stop:
                self.trips_at.setdefault(event.stop, set()).add(trip)

    def _rules(self) -> str:
        files = [p for p in sorted(self.workspace.glob("*.fx")) if p.name[:2] < "60"]
        policy = importlib.resources.files("framex") / "policies" / "competence.fx"
        parts = [p.read_text(encoding="utf-8") for p in files]
        return "\n".join([*parts, policy.read_text(encoding="utf-8"), GATE.read_text(encoding="utf-8")])

    # --- stations ---------------------------------------------------------

    def station_id(self, name: str) -> str | None:
        """The exact designation check of the language contract."""
        ids = self.ids_by_name.get(name)
        return ids[0] if ids else None

    def official_name(self, text: str) -> str | None:
        """The designation the passenger's own words spell, if exactly one does."""
        names = self._by_fold.get(fold(text), [])
        return names[0] if len(names) == 1 else None

    def _service(self, name: str) -> int:
        return max(len(self.trips_at.get(sid, ())) for sid in self.ids_by_name[name])

    def candidates(self, name: str, limit: int = 8) -> list[str]:
        """Official designations a city name could mean, busiest first."""
        key = fold(name)
        if not key:
            return []
        names = [n for folded, group in self._by_fold.items()
                 if folded == key or folded.startswith(key + " ") for n in group]
        names = [n for n in names if self._service(n) > 0]
        return sorted(names, key=lambda n: (-self._service(n), n))[:limit]

    def bare_city_stations(self, quote: str, station: str) -> list[str]:
        """The stations meant if the passenger named only a city and the model picked one."""
        official = fold(station)
        words = fold(quote).split()
        # A quote may carry a preposition: "to Zürich" still names only the city.
        for start in range(len(words)):
            tail = " ".join(words[start:])
            if official.startswith(tail + " ") and len(found := self.candidates(tail)) > 1:
                return found
        return []

    # --- worlds -----------------------------------------------------------

    def _touches(self, trip: str, stop: str, low: int, high: int) -> bool:
        return any(e.stop == stop and any(low <= t <= high for t in e.times) for e in self.events[trip])

    def select_trips(self, origin: str, destination: str, low: int, high: int) -> list[str]:
        """Every trip the refund rules can use for this case, and few others."""
        latest_board = high + self.max_start_wait
        latest_arrival = latest_board + self.max_journey
        first = {t for t in self.trips_at.get(origin, ()) if self._touches(t, origin, low, latest_board)}
        windows: dict[str, list[tuple[int, int]]] = {}
        for trip in first:
            boarded = min(e.sequence for e in self.events[trip] if e.stop == origin)
            for event in self.events[trip]:
                if event.sequence > boarded and event.times:
                    windows.setdefault(event.stop, []).append((min(event.times), max(event.times)))
        chosen = set(first)
        for trip in self.trips_at.get(destination, ()):
            if trip in chosen or not self._touches(trip, destination, low, latest_arrival):
                continue
            alight = max(e.sequence for e in self.events[trip] if e.stop == destination)
            if any(event.sequence < alight and self._fits(event, windows) for event in self.events[trip]):
                chosen.add(trip)
        # One real trip always loads, so the rule that asks whether the day is
        # on record sees the snapshot's day even when no train fits the window.
        chosen.add(next(iter(self.blocks)))
        return sorted(chosen)

    def _fits(self, event: _Event, windows: dict[str, list[tuple[int, int]]]) -> bool:
        spans = windows.get(event.stop, ())
        return any(low <= t <= high + self.max_change_wait for low, high in spans for t in event.times)

    def _facts(self, trips: list[str]) -> list[str]:
        lines = [line for trip in trips for line in self.blocks[trip]]
        stops = sorted({found.group(1) for line in lines if (found := _STOP.search(line))})
        named = [f"{stop}[designation -> {_literal(self.names[stop])}]." for stop in stops if stop in self.names]
        return [*(f"{stop}:StopPoint." for stop in stops), *named, *lines]

    @staticmethod
    def _case_fact(case: Case, low: int, high: int) -> str:
        return (f"x:RefundCase[origin -> {case.origin_id}; destination -> {case.destination_id}; "
                f"onDay -> {_literal(case.day)}; windowFrom -> {low}; windowTo -> {high}; "
                f"transferSeconds -> {TRANSFER_SECONDS}].")

    @staticmethod
    def _window(case: Case) -> tuple[int, int]:
        stated = service.timestamp(f"{case.day}T{case.time}:00")
        if stated is None:
            raise ValueError(f"not a valid local time: {case.day} {case.time}")
        return stated - WINDOW_SECONDS, stated + WINDOW_SECONDS

    def offers(self, case: Case) -> OfferResult:
        """The departures the rules offer, or why this day cannot be checked."""
        started = time.monotonic()
        low, high = self._window(case)
        trips = self.select_trips(case.origin_id, case.destination_id, low, high)
        fact = self._case_fact(case, low, high)
        with World(self.rules, [*self._facts(trips), fact]) as world:
            why_not = world.value("x", "notCheckable")
            groups: dict[tuple, list[str]] = {}
            for row in world.rows("?- x[offered(?E) -> ?A] AND ?E[scheduledDepartureEpoch -> ?D].") if not why_not else []:
                board = row["E"]
                trip = world.value(board, "ofTrip")
                label = world.value(trip, "lineText") or world.value(trip, "serviceCategory") or "train"
                changes = world.value("x", f"plannedChanges({board})") or 0
                groups.setdefault((int(row["D"]), int(row["A"]), label, changes), []).append(board)
        offers = [
            Offer(f"t{index}", label, clock(departure), clock(arrival), changes, tuple(sorted(boards)))
            for index, ((departure, arrival, label, changes), boards) in enumerate(sorted(groups.items()), 1)
        ]
        return OfferResult(offers, why_not, fact, len(trips), time.monotonic() - started)

    def verdict(self, case: Case, offer: Offer, price_rappen: int | None) -> Verdict:
        """Run `DelayCheck` and the policy for the chosen departure."""
        started = time.monotonic()
        low, high = self._window(case)
        trips = self.select_trips(case.origin_id, case.destination_id, low, high)
        price = f"; ticketPriceRappen -> {price_rappen}" if price_rappen is not None else ""
        journey = (f"{case.origin_name} to {case.destination_name} on {case.day}, "
                   f"planned departure {offer.departure}, train {offer.label}.")
        facts = [self._case_fact(case, low, high)]
        checks = [f"y{index}" for index in range(len(offer.boards))]
        for check, board in zip(checks, offer.boards, strict=True):
            facts.append(f"{check}:DelayCheck[checkOf -> x; plannedBoard -> {board}{price}].")
            facts.append(f"{check}:cp#Case[cp#file -> {_literal(journey)}; cp#prompt -> assessPrompt].")
        with World(self.rules, [*self._facts(trips), *facts]) as world:
            verdicts = [self._read(world, check) for check in checks]
        chosen = verdicts[0]
        chosen.asserted = "\n".join(facts)
        chosen.trips = len(trips)
        chosen.seconds = time.monotonic() - started
        if any((v.decision, v.percent) != (chosen.decision, chosen.percent) for v in verdicts):
            chosen.decision, chosen.outcome = "handoff", "handoff"
            chosen.reason = "this departure appears twice in the data with different results"
        return chosen

    def _read(self, world: World, check: str) -> Verdict:
        rules = {slot: world.value("refundPolicy", slot) for slot in ("thresholdMinutes", "minimumPayoutRappen")}
        result = Verdict(
            decision="handoff", outcome="handoff",
            delay_minutes=world.value(check, "delayMinutes"),
            planned_arrival=clock(world.value(check, "plannedArrival")),
            actual_arrival=clock(world.value(check, "actualArrival")),
            cancelled=bool(world.value(check, "planCancelled")),
            threshold_minutes=rules["thresholdMinutes"],
            minimum_rappen=rules["minimumPayoutRappen"],
        )
        status = world.value(check, "refundStatus")
        result.percent = world.value(check, "refundPercent")
        result.refund_rappen = world.value(check, "refundRappen")
        paid_out = world.value(check, "paidOut")
        if world.value(check, "cp#handOn") is True:
            result.reason = world.value(check, "handOff") or "the rules could not decide this case"
            result.assessment = self._assessment(world, check, result.reason)
            return result
        if status == "entitled":
            result.decision = "no_refund" if paid_out is False else "refund"
            result.outcome = {None: "refund_percent", True: "refund_amount", False: "below_minimum"}[paid_out]
        elif status == "notEntitled":
            result.decision = "no_refund"
            result.outcome = "on_time" if result.delay_minutes == 0 else "no_refund"
        result.proof = world.proof(f"{check}[refundPercent -> {result.percent}]")
        return result

    @staticmethod
    def _assessment(world: World, check: str, reason: str) -> dict | None:
        """Pattern 7: the library's own request for this case, if it made one."""
        for row in world.rows("?- ?Call[tool#requested -> true; tool#arg1 -> ?C]."):
            if row["C"] == check:
                fields = {r["K"]: _decode(r["V"]) for r in world.rows(f"?- {row['Call']}[?K -> ?V].")}
                return {"prompt": fields.get("prompt"), "file": f"{fields.get('file')} Not decided because: {reason}."}
        return None
