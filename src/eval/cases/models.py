"""Shared evaluation case model; scenario values live in config/eval YAML."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

Json = dict[str, Any]
DECISIONS = {"refund", "no_refund", "handoff", "question", "error"}


@dataclass
class Case:
    id: str
    request: Json
    expected: Json
    tags: list[str] = field(default_factory=list)
    messages: list[Json] = field(default_factory=list)
    must_say: list[str] = field(default_factory=list)
    expected_tools: list[Json] | None = None
    snapshot: dict[str, str] = field(default_factory=dict)
    evidence: Json = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Json) -> Case:
        case = cls(**raw)
        if not isinstance(case.id, str) or not case.id:
            raise ValueError("case id must be a nonempty string")
        if not isinstance(case.request, dict) or not isinstance(case.expected, dict):
            raise TypeError("case request and expected must be objects")
        if case.expected.get("decision") not in DECISIONS:
            raise ValueError("case expected decision is invalid")
        for values in (case.tags, case.must_say):
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ValueError("tags and must_say must be string lists")
        if not isinstance(case.messages, list) or any(
            not isinstance(m, dict) or m.get("role") not in {"user", "assistant"}
            or not isinstance(m.get("content"), str) for m in case.messages
        ):
            raise ValueError("messages must be scripted user/assistant messages")
        if case.expected_tools is not None and any(
            not isinstance(c, dict) or not isinstance(c.get("name"), str)
            or not isinstance(c.get("arguments"), dict) for c in case.expected_tools
        ):
            raise ValueError("expected_tools requires name and arguments")
        if not isinstance(case.snapshot, dict) or not isinstance(case.evidence, dict):
            raise TypeError("snapshot/evidence must be objects")
        if case.request.get("price_chf") is not None and not isinstance(case.request["price_chf"], str):
            raise TypeError("price_chf must be a quoted decimal string")
        if case.expected.get("refundCHF") is not None and not isinstance(case.expected["refundCHF"], str):
            raise TypeError("refundCHF must be a quoted decimal string")
        return case

    def to_dict(self) -> Json:
        return asdict(self)


