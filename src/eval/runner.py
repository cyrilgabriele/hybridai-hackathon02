"""Run cases through ports, isolate failures, and report honest denominators."""

from __future__ import annotations

import json
import math
import statistics
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .cases import load_cases  # noqa: F401 -- compatibility for the initial runner import
from .contracts import Case, JudgePort, Observation, SystemInput, SystemPort
from .metrics import evaluate


def durations(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "median_ms": None, "p95_ms": None}
    ordered = sorted(values)
    return {"count": len(values), "median_ms": statistics.median(values),
            "p95_ms": ordered[math.ceil(0.95 * len(values)) - 1]}


def run_cases(system: SystemPort, cases: list[Case], *, repeats: int = 1,
              judge: JudgePort | None = None, progress: Callable[[str], None] | None = None) -> dict:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    rows = []
    cleanup_error = None
    try:
        for repetition in range(repeats):
            for case in cases:
                if progress:
                    progress(f"{case.id}: attempt {repetition + 1}/{repeats}")
                start = time.perf_counter()
                try:
                    request = SystemInput(case.id, deepcopy(case.request), deepcopy(case.messages), case.snapshot.copy())
                    result = Observation.from_dict(asdict(system.run(request)))
                except Exception as exc:  # noqa: BLE001 -- each attempted case remains in the report
                    result = Observation("error", error=type(exc).__name__)
                elapsed = (time.perf_counter() - start) * 1000
                performance_eligible = result.metadata.get("performance_eligible", True)
                replay = system.scope == "replay"
                latency = result.stage_ms.get("end_to_end") if replay else elapsed
                effective_scope = result.metadata.get("scope", "conversation") if replay else system.scope
                scores = evaluate(case, result, scope=effective_scope)
                quality = {"status": "unscored", "reason": "judge disabled"}
                judge_ms = None
                if judge is not None and result.reply and not result.error:
                    judge_start = time.perf_counter()
                    try:
                        quality = {"status": "scored", **judge.score(case, result)}
                    except Exception as exc:  # noqa: BLE001 -- judge failures do not erase system results
                        quality = {"status": "error", "error_type": type(exc).__name__}
                    judge_ms = (time.perf_counter() - judge_start) * 1000
                rows.append({"case_id": case.id, "repetition": repetition, "tags": case.tags,
                             "case": case.to_dict(), "expected": case.expected, "observation": asdict(result),
                             "scope": effective_scope,
                             "phase": "first_request" if not rows else "warm_request",
                             "replayed": replay, "performance_eligible": performance_eligible, "latency_ms": latency,
                             "judge_ms": judge_ms, "scores": scores, "quality": quality})
                if progress:
                    progress(f"{case.id}: correct={scores['correct']}, elapsed_ms={latency}")
    finally:
        try:
            system.close()
        except Exception as exc:  # noqa: BLE001 -- retain completed measurements even if cleanup fails
            cleanup_error = type(exc).__name__
    return {"version": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
            "rubric_version": "refund-quality-v1", "percentile_method": "nearest-rank",
            "system": type(system).__name__, "scope": system.scope,
            "system_configuration": getattr(system, "configuration", {}),
            "initialization_ms": getattr(system, "initialization_ms", None),
            "cleanup_error": cleanup_error,
            "rows": rows, "summary": summarize(rows)}


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row["case_id"], []).append(row)
    consistency = []
    for group in groups.values():
        if len(group) < 2:
            continue
        outcomes = {json.dumps({"decision": r["observation"]["decision"],
                                "facts": r["observation"]["facts"]}, sort_keys=True) for r in group}
        consistency.append(len(outcomes) == 1)
    metrics = {}
    for key in ("tool_precision", "tool_recall", "parameter_accuracy", "required_content_coverage"):
        values = [r["scores"][key] for r in rows if r["scores"][key] is not None]
        metrics[key] = {"count": len(values), "mean": statistics.mean(values) if values else None}
    stages: dict[str, list[float]] = {}
    for row in rows:
        if row.get("performance_eligible", True):
            for name, value in row["observation"]["stage_ms"].items():
                stages.setdefault(name, []).append(value)
    quality_dimensions: dict[str, list[int]] = {}
    for row in rows:
        if row["quality"].get("status") == "scored":
            for name, rating in row["quality"].get("ratings", {}).items():
                quality_dimensions.setdefault(name, []).append(rating["score"])
    return {"attempted": total, "correct": sum(r["scores"]["correct"] for r in rows),
            "task_successes": sum(r["scores"]["task_success"] for r in rows),
            "technical_errors": sum(r["observation"]["decision"] == "error" for r in rows),
            "audit_complete": sum(r["scores"]["audit_complete"] for r in rows),
            "invariant_counts": invariant_counts(rows),
            "latency": durations([r["latency_ms"] for r in rows if r["latency_ms"] is not None and r.get("performance_eligible", True)]),
            "first_request": durations([r["latency_ms"] for r in rows if r["phase"] == "first_request" and r["latency_ms"] is not None and r.get("performance_eligible", True)]),
            "warm_request": durations([r["latency_ms"] for r in rows if r["phase"] == "warm_request" and r["latency_ms"] is not None and r.get("performance_eligible", True)]),
            "judge_latency": durations([r["judge_ms"] for r in rows if r["judge_ms"] is not None]),
            "stages": {name: durations(values) for name, values in stages.items()},
            "repeated_cases": len(consistency),
            "decision_consistency": sum(consistency) / len(consistency) if consistency else None,
            "quality_scored": sum(r["quality"].get("status") == "scored" for r in rows),
            "quality_errors": sum(r["quality"].get("status") == "error" for r in rows),
            "quality_proxy": {name: {"count": len(values), "mean": statistics.mean(values)}
                              for name, values in quality_dimensions.items()}, **metrics}


def invariant_counts(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        for invariant, status in row["scores"]["invariants"].items():
            key = f"{invariant}.{status}"
            counts[key] = counts.get(key, 0) + 1
    return counts


def write_report(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    summary = report["summary"]
    lines = ["# Refund evaluation", "", f"Scope: {report['scope']}. System: {report['system']}.",
             "Quality scores are automated proxies, not measured user satisfaction.", "",
             (f"Attempted: {summary['attempted']}; correct: {summary['correct']}; "
              f"task successes: {summary['task_successes']}; technical errors: {summary['technical_errors']}."),
             f"Audit-complete runs: {summary['audit_complete']}. Missing instrumentation is unverified.", "",
             "| Case | Repeat | Correct | Task success | Latency ms | Quality |",
             "|---|---:|---|---|---:|---|"]
    for row in report["rows"]:
        lines.append(f"| {row['case_id']} | {row['repetition']} | {row['scores']['correct']} | "
                     f"{row['scores']['task_success']} | {row['latency_ms']} | {row['quality']['status']} |")
    lines += ["", "## Aggregate measurements", "", "```json", json.dumps(summary, indent=2), "```", ""]
    (output / "summary.md").write_text("\n".join(lines))
