"""Deterministic scores: no model judgment can override these checks."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .contracts import Case, Observation


def tool_metrics(events: list[dict], expected: list[dict] | None) -> dict:
    if expected is None:
        return {"tool_precision": None, "tool_recall": None, "parameter_accuracy": None}
    predicted = [e for e in events if e.get("kind") == "execute"]
    names = Counter(e.get("name") for e in predicted)
    required = Counter(e["name"] for e in expected)
    hits = sum((names & required).values())
    remaining = predicted.copy()
    matched = 0
    for call in expected:
        index = next((i for i, e in enumerate(remaining)
                      if e.get("name") == call["name"] and e.get("arguments") == call["arguments"]), None)
        if index is not None:
            matched += 1
            remaining.pop(index)
    return {"tool_precision": hits / len(predicted) if predicted else float(not expected),
            "tool_recall": hits / len(expected) if expected else 1.0,
            "parameter_accuracy": matched / len(expected) if expected else float(not predicted)}


def invariants(result: Observation) -> dict[str, str]:
    """Check ordered call IDs and evidence anchors; coverage alone is insufficient."""
    validations = {}
    executions = []
    acceptance = []
    for event in result.events:
        call_id = event.get("call_id")
        if event.get("kind") == "validate" and event.get("approved") is True and call_id:
            validations[call_id] = event
        if event.get("kind") == "execute":
            validation = validations.get(call_id, {})
            executions.append(bool(call_id and call_id in validations
                                   and event.get("name") == validation.get("name")
                                   and event.get("arguments") == validation.get("arguments")))
        if event.get("kind") == "accept":
            refs = event.get("evidence", [])
            anchors = result.metadata.get("evidence", {})
            acceptance.append(bool(refs) and all(ref in anchors and anchors[ref] for ref in refs))
    repairs = [e for e in result.events if e.get("kind") == "repair"]
    repair_counts = Counter(e.get("scope_id", "unscoped") for e in repairs)
    verdict = {}
    for key, checks in (("checked_execution", executions), ("evidence_acceptance", acceptance)):
        if checks and not all(checks):
            verdict[key] = "failed"
        elif key not in result.coverage or not checks:
            verdict[key] = "unverified"
        else:
            verdict[key] = "passed"
    verdict["repair_budget"] = (
        "failed" if any(count > 1 for count in repair_counts.values()) else "passed"
        if "repair_budget" in result.coverage else "unverified")
    price_questions = [e for e in result.events if e.get("kind") == "ask" and e.get("slot") == "price"]
    verdict["price_asked_once"] = (
        "failed" if len(price_questions) > 1 else "passed" if "price_asked_once" in result.coverage else "unverified")
    verdict["replayable"] = "passed" if all(
        result.metadata.get(k) for k in ("timestamp", "system_version", "model", "receipt_id")
    ) else "unverified"
    return verdict


def evaluate(case: Case, result: Observation, *, scope: str) -> dict[str, Any]:
    actual = {"decision": result.decision, **result.facts}
    # The transport decision cannot be overridden by a contradictory facts field.
    actual["decision"] = result.decision
    checks = {key: actual.get(key) == value for key, value in case.expected.items()}
    if result.error is not None or result.decision == "error":
        checks["no_technical_failure"] = case.expected["decision"] == "error"
    if result.decision in {"handoff", "question", "error"}:
        checks["no_unsupported_verdict"] = all(
            result.facts.get(key) is None for key in ("refundStatus", "refundPercent", "refundCHF", "paidOut"))
    present = [bool(re.search(r"(?<!\d)" + re.escape(phrase) + r"(?!\d)", result.reply, re.IGNORECASE))
               if phrase.isdigit() else phrase.casefold() in result.reply.casefold() for phrase in case.must_say]
    communication = None if scope == "component" else all(present) and bool(result.reply.strip())
    scores = tool_metrics(result.events, case.expected_tools)
    guards = invariants(result)
    slots = [event for event in result.events if event.get("kind") == "slot" and event.get("accepted") is True]
    quote_checks = []
    for slot in slots:
        index, quote = slot.get("message_index"), slot.get("quote")
        quote_checks.append(type(index) is int and 0 <= index < len(case.messages)
                            and isinstance(quote, str) and bool(quote.strip())
                            and quote.casefold() in case.messages[index]["content"].casefold())
    quote_fidelity = (sum(quote_checks) / len(quote_checks)) if quote_checks else None
    if quote_fidelity is not None:
        checks["accepted_quotes_grounded"] = quote_fidelity == 1.0
    correct = all(checks.values())
    tools_ok = all(v in (None, 1.0) for v in scores.values())
    return {"correct": correct, "checks": checks,
            "required_content_coverage": sum(present) / len(present) if present and scope != "component" else None,
            **scores, "quote_fidelity": quote_fidelity, "invariants": guards,
            "task_success": correct and tools_ok and (scope == "component" or communication is True)
            and not any(v == "failed" for v in guards.values()),
            "audit_complete": all(v == "passed" for v in guards.values())}
