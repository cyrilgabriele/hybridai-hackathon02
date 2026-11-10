"""Ports and JSON records shared with refund conversation adapters."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from .cases.models import DECISIONS, Case, Json


@dataclass
class Observation:
    decision: str
    reply: str = ""
    facts: Json = field(default_factory=dict)
    events: list[Json] = field(default_factory=list)
    coverage: list[str] = field(default_factory=list)
    stage_ms: dict[str, float] = field(default_factory=dict)
    usage: Json = field(default_factory=dict)
    metadata: Json = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def from_dict(cls, raw: Json) -> Observation:
        result = cls(**raw)
        if result.decision not in DECISIONS or not isinstance(result.reply, str):
            raise ValueError("invalid observation decision/reply")
        if not isinstance(result.facts, dict) or not isinstance(result.metadata, dict):
            raise TypeError("observation facts/metadata must be objects")
        if not isinstance(result.stage_ms, dict) or not isinstance(result.usage, dict):
            raise TypeError("stage_ms/usage must be objects")
        if not isinstance(result.events, list) or not all(isinstance(e, dict) for e in result.events):
            raise ValueError("events must be objects")
        for event in result.events:
            for name in ("kind", "call_id", "name", "scope_id"):
                if name in event and not isinstance(event[name], str):
                    raise ValueError("event kind, call_id and name must be strings")
            if "arguments" in event and not isinstance(event["arguments"], dict):
                raise ValueError("event arguments must be an object")
            if "evidence" in event and (not isinstance(event["evidence"], list)
                                       or not all(isinstance(ref, str) for ref in event["evidence"])):
                raise ValueError("event evidence must be string references")
        if not isinstance(result.metadata.get("evidence", {}), dict):
            raise TypeError("metadata evidence must be an object of anchors")
        if not all(isinstance(v, (float, int)) and not isinstance(v, bool)
                   and math.isfinite(v) and v >= 0 for v in result.stage_ms.values()):
            raise ValueError("stage_ms must contain finite nonnegative durations")
        if not isinstance(result.coverage, list) or not all(isinstance(v, str) for v in result.coverage):
            raise ValueError("coverage must be a list of instrumentation names")
        return result


@dataclass(frozen=True)
class SystemInput:
    """No expected outcomes, oracle evidence, or scoring instructions cross this port."""

    id: str
    request: Json
    messages: list[Json]
    snapshot: dict[str, str]


class SystemPort(Protocol):
    scope: str  # 'component', 'conversation', or 'replay'

    def run(self, case: SystemInput, /) -> Observation: ...

    def close(self) -> None: ...


class JudgePort(Protocol):
    def score(self, case: Case, observation: Observation, /) -> Json: ...
