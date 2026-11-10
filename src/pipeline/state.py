"""The state of one passenger conversation and its trace for the workflow view."""

from __future__ import annotations

from dataclasses import dataclass, field

from .knowledge import Offer, Verdict


@dataclass
class Step:
    """One thing that happened. Failed, refused, unknown and handed on stay distinct."""

    pattern: str
    actor: str
    title: str
    detail: str = ""
    status: str = "ok"  # ok | repair | refused | unknown | handed_on | failed
    seconds: float = 0.0
    sent: str = ""  # what the host sent to the model, for the workflow view


@dataclass
class Slot:
    """A value the host accepted, with the passenger's own words behind it."""

    value: str
    quote: str
    station_id: str | None = None


@dataclass
class Conversation:
    events: list[dict] = field(default_factory=list)
    evidence: dict[str, dict] = field(default_factory=dict)
    decision: str = "question"
    critique_reason: str | None = None
    error: str | None = None
    turn: int = 0
    context: list[dict[str, str]] = field(default_factory=list)
    message_indices: list[int] = field(default_factory=list)
    input_message_count: int = 0
    messages: list[str] = field(default_factory=list)
    slots: dict[str, Slot] = field(default_factory=dict)
    language: str = "en"
    stage: str = "collect"  # collect | choose_train | price | done | handed_over
    asked_for: str | None = None
    pending_station: tuple[str, str, list[str]] | None = None
    unknown_asked: dict[str, int] = field(default_factory=dict)
    told: set[str] = field(default_factory=set)
    time_asked_again: bool = False
    train_asked_again: bool = False
    price_asked: bool = False
    offers: list[Offer] = field(default_factory=list)
    chosen: Offer | None = None
    verdict: Verdict | None = None
    handoff_id: str | None = None
    decision_delivered: bool = False
    trace: list[Step] = field(default_factory=list)

    def record(self, kind: str, **data) -> None:
        self.events.append({"kind": kind, **data})

    def accept(self, name: str, evidence: dict) -> None:
        anchor = f"e{len(self.evidence)}"
        self.evidence[anchor] = evidence
        self.record("accept", name=name, evidence=[anchor])

    def start_new_case(self) -> None:
        """A new journey in the same chat keeps only the language and the trace."""
        fresh = Conversation(language=self.language, trace=self.trace, events=self.events,
                             evidence=self.evidence, turn=self.turn, input_message_count=self.input_message_count)
        self.__dict__.update(fresh.__dict__)
