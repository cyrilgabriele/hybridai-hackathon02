"""Conversation port for the actual assistant; expectations never enter this module.

The default factory makes fresh live model calls. Set REFUND_EVAL_MODE=replay
for recorded-only evaluation (a missing recording is an error, never a live call).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import distribution
from pathlib import Path

from eval.contracts import Observation, SystemInput
from eval.snapshot import fingerprint
from runtime.query import binary

from .assistant import Assistant
from .handoff import Desk
from .knowledge import WORKSPACE, Knowledge, Offer, OfferResult
from .llm import MODEL, LanguageModel, ModelAnswer, ModelCallFailed
from .slots import EXTRACT_PROMPT
from .state import Conversation

FAULTS = {"fabricated_quote_after_repair", "model_timeout", "tool_timeout",
          "repair_exhausted", "several_departures_after_correction"}


class EvaluationModel(LanguageModel):
    """Record measured calls; inject only declared adversarial model responses."""

    def __init__(self, store: Path, *, mode: str, fault: str | None = None):
        super().__init__(store, refresh=mode == "live")
        self.mode = mode
        self.fault = fault
        self.calls: list[dict] = []

    def ask_json(self, system: str, user: str, *, effort="low") -> ModelAnswer:
        started = time.perf_counter()
        answer = None
        try:
            if system == EXTRACT_PROMPT and self.fault == "model_timeout":
                raise ModelCallFailed("injected timeout")
            if system == EXTRACT_PROMPT and self.fault in {"fabricated_quote_after_repair", "repair_exhausted"}:
                data = ({"origin": {"station": "Bern", "quote": "invented passenger evidence"}}
                        if self.fault == "fabricated_quote_after_repair" else None)
                answer = ModelAnswer(data, json.dumps(data), "injected", "", 0.0)
            else:
                if self.mode == "replay":
                    identity = json.dumps([MODEL, [{"role": "system", "content": system},
                                                  {"role": "user", "content": user}]],
                                          ensure_ascii=False, sort_keys=True)
                    path = self.store / f"{hashlib.sha256(identity.encode()).hexdigest()[:24]}.json"
                    if not path.is_file():
                        raise ModelCallFailed("evaluation recording unavailable")
                    # Do not let the application's refresh env override replay-only mode.
                    stored = json.loads(path.read_text())
                    raw = stored["raw"]
                    try:
                        data = json.loads(raw)
                    except ValueError:
                        data = None
                    answer = ModelAnswer(data if isinstance(data, dict) else None, raw, "replay",
                                         stored["recorded_at"], 0.0, stored.get("usage", {}))
                else:
                    answer = super().ask_json(system, user, effort=effort)
            return answer
        finally:
            self.calls.append({"mode": answer.mode if answer else "error",
                               "stage": "extraction" if system == EXTRACT_PROMPT else "generation",
                               "elapsed_ms": (time.perf_counter() - started) * 1000,
                               "usage": answer.usage if answer and answer.mode == "live" else {}})


class FaultKnowledge(Knowledge):
    """Explicit test boundary, leaving the shared production knowledge untouched."""

    def __init__(self, knowledge: Knowledge, fault: str | None):
        self.__dict__.update(knowledge.__dict__)
        self.fault = fault

    def offers(self, case):
        if self.fault == "tool_timeout":
            raise TimeoutError("injected engine timeout")
        if self.fault == "several_departures_after_correction":
            # The scenario controls ambiguity; the host still validates the corrected slots.
            return OfferResult([Offer("fixture1", "IC A", "08:00", "09:00", 0, ()),
                                Offer("fixture2", "IC B", "08:05", "09:05", 0, ())],
                               None, "test fixture: two departures", 0, 0.0)
        return super().offers(case)


def system_version() -> str:
    """Hash actual source, including uncommitted changes, rather than just HEAD."""
    digest = hashlib.sha256()
    root = Path(__file__).resolve().parents[1]
    for package in ("pipeline", "runtime", "ontology"):
        for path in sorted((root / package).rglob("*")):
            if path.suffix in {".py", ".fx"}:
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


class RefundSystemAdapter:
    scope = "conversation"

    def __init__(self, knowledge: Knowledge | None = None, *, mode: str = "live",
                 store: Path = Path("eval-results/model-answers"), model_factory=None):
        if mode not in {"live", "replay"}:
            raise ValueError("evaluation mode must be live or replay")
        started = time.perf_counter()
        self.knowledge = knowledge if knowledge is not None else Knowledge()
        self.hashes = fingerprint(self.knowledge.workspace)
        self.version = system_version()
        self.mode, self.store, self.model_factory = mode, store, model_factory
        package = distribution("framex")
        direct = json.loads(package.read_text("direct_url.json") or "{}")
        commit = direct.get("vcs_info", {}).get("commit_id")
        receipt = Path(binary()).parent.parent / ".crates.toml"
        matches = commit in receipt.read_text() if commit and receipt.is_file() else None
        if matches is False:
            raise ValueError("installed FrameX engine and client commits do not match")
        self.configuration = {"client_version": package.version, "client_commit": commit,
                              "engine_receipt_matches_client": matches, "model": MODEL, "mode": mode, "workspace": str(self.knowledge.workspace),
                              "system_version": self.version, "snapshot": self.hashes}
        self.initialization_ms = (time.perf_counter() - started) * 1000

    def run(self, case: SystemInput) -> Observation:
        if case.snapshot and case.snapshot != self.hashes:
            raise ValueError("case snapshot does not match production workspace")
        if not case.messages or "synthetic_delay" in case.request:
            raise ValueError("conversation evaluation requires passenger messages")
        fault = case.request.get("fault")
        if fault is not None and fault not in FAULTS:
            raise ValueError("unknown evaluation fault")
        model = (self.model_factory() if self.model_factory else
                 EvaluationModel(self.store, mode=self.mode, fault=fault))
        knowledge = FaultKnowledge(self.knowledge, fault) if fault else self.knowledge
        assistant = Assistant(knowledge, model, Desk())
        conv = Conversation()
        transcript = []
        user_indices = []
        reply = ""
        started = time.perf_counter()
        for index, message in enumerate(case.messages):
            if message["role"] == "user":
                user_indices.append(index)
                transcript.append(dict(message))
                reply = assistant.handle(conv, message["content"])
                transcript.append({"role": "assistant", "content": reply, "generated": True})
            elif message["role"] == "assistant":
                # Fixture context is recorded, never passed off as generated output.
                conv.context.append(dict(message))
                transcript.append({**message, "generated": False})
            else:
                raise ValueError("only user and assistant dialogue roles are supported")
        if not user_indices:
            raise ValueError("conversation has no passenger turn")
        for event in conv.events:
            if event.get("kind") == "slot" and event.get("accepted"):
                event["message_index"] = user_indices[event["message_index"]]
        for evidence in conv.evidence.values():
            if "message_index" in evidence:
                evidence["message_index"] = user_indices[evidence["message_index"]]
        facts = {}
        if conv.verdict:
            facts = conv.verdict.facts.copy()
            rappen = facts.pop("refundRappen", None)
            facts["refundCHF"] = f"{rappen / 100:.2f}" if rappen is not None else None
        if conv.decision in {"question", "handoff", "error"}:
            for key in ("refundStatus", "refundPercent", "refundCHF", "paidOut"):
                facts[key] = None
        if conv.critique_reason:
            facts["critiqueReason"] = conv.critique_reason
        for name in ("origin", "destination"):
            if name in conv.slots:
                facts[name] = conv.slots[name].station_id
        calls = getattr(model, "calls", [])
        modes = sorted({c["mode"] for c in calls})
        usage: dict = {}
        for call in calls:
            for key, value in call["usage"].items():
                if type(value) is int:
                    usage[key] = usage.get(key, 0) + value
        stages = {"end_to_end": (time.perf_counter() - started) * 1000}
        for call in calls:
            name = "model_" + call["stage"]
            stages[name] = stages.get(name, 0.0) + call["elapsed_ms"]
        stages["engine"] = sum(step.seconds * 1000 for step in conv.trace if step.actor == "Rules")
        return Observation(conv.decision, reply, facts, conv.events,
                           ["checked_execution", "evidence_acceptance", "repair_budget", "price_asked_once"],
                           stages, usage, {"timestamp": datetime.now(timezone.utc).isoformat(),
                                           "system_version": self.version, "model": MODEL,
                                           "receipt_id": uuid.uuid4().hex, "evidence": conv.evidence,
                                           "transcript": transcript, "workflow": [asdict(step) for step in conv.trace],
                                           "model_calls": calls, "model_modes": modes,
                                           "performance_eligible": bool(calls) and self.mode == "live"
                                           and not set(modes) & {"replay", "injected"} and not fault,
                                           "fault": fault, "fixture_controlled": bool(fault),
                                           "snapshot": self.hashes, "configuration": self.configuration}, conv.error)

    def close(self) -> None:
        # Knowledge holds indexes only; each engine closes in production's World context manager.
        pass


def create() -> RefundSystemAdapter:
    return RefundSystemAdapter(mode=os.environ.get("REFUND_EVAL_MODE", "live"),
                               store=Path(os.environ.get("REFUND_EVAL_STORE", "eval-results/model-answers")),
                               knowledge=Knowledge(Path(os.environ.get("REFUND_EVAL_WORKSPACE", str(WORKSPACE)))))
