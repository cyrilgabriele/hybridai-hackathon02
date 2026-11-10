"""The customer-service desk: cases the rules left open (pattern 7).

A person decides here. The decision is asserted as a FrameX fact and read back,
so a percentage shown to the passenger comes from facts here too.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime

from runtime.client import Client
from runtime.query import binary

from .knowledge import ZONE


@dataclass
class HandOff:
    id: str
    journey: dict[str, tuple[str, str]]  # slot -> (value, the passenger's words)
    train: str
    reason: str
    assessment: str
    note: str
    messages: list[str]
    opened: str
    status: str = "open"  # open | decided
    outcome: str = ""
    percent: int = 0
    comment: str = ""

    def choice(self) -> str:
        route = f"{self.journey.get('origin', ('?', ''))[0]} to {self.journey.get('destination', ('?', ''))[0]}"
        return f"{self.id}: {route}"

    def file(self) -> str:
        """The case file the officer reads."""
        lines = [f"### Case {self.id}", f"**Why the rules could not decide:** {self.reason}", ""]
        lines += [f"- **{slot}:** {value} (passenger wrote: \"{quote}\")" for slot, (value, quote) in self.journey.items()]
        if self.train:
            lines.append(f"- **train:** {self.train}")
        lines += ["", f"**Model's note (advisory, decides nothing):** {self.assessment or 'none'}: {self.note}"]
        lines += ["", "**The passenger wrote:**", *(f"> {message}" for message in self.messages)]
        return "\n".join(lines)


class Desk:
    """Open cases in memory; handlers on several threads share it."""

    def __init__(self) -> None:
        self._cases: dict[str, HandOff] = {}
        self._lock = threading.Lock()

    def open(self, case: HandOff) -> HandOff:
        with self._lock:
            self._cases.setdefault(case.id, case)
            return self._cases[case.id]

    def get(self, case_id: str | None) -> HandOff | None:
        with self._lock:
            return self._cases.get(case_id) if case_id else None

    def open_choices(self) -> list[str]:
        with self._lock:
            return [case.choice() for case in self._cases.values() if case.status == "open"]

    def decide(self, case_id: str, outcome: str, percent: int, comment: str) -> HandOff:
        """Record a person's decision as a fact and read the share back from it."""
        case = self.get(case_id)
        if case is None:
            raise KeyError(case_id)
        share = percent if outcome == "refund" else 0
        fact = (f"world open.\nhd:HumanDecision[caseRef -> {json.dumps(case_id)}; outcome -> {json.dumps(outcome)}; "
                f'percent -> {int(share)}; decidedBy -> "SBB customer service"].')
        with Client(binary()) as client:
            client.request("load", source=fact)
            bindings = client.query("?- hd[percent -> ?P].").get("bindings", [])
        with self._lock:
            case.status, case.outcome, case.comment = "decided", outcome, comment
            case.percent = int(bindings[0]["P"])
        return case


def now() -> str:
    return datetime.now(ZONE).strftime("%Y-%m-%d %H:%M")
