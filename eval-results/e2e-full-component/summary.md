# Refund evaluation

Scope: component. System: FrameXSystem.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 7; correct: 7; task successes: 7; technical errors: 0.
Audit-complete runs: 0. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| snapshot_no_refund | 0 | True | True | 8643.882332951762 | unscored |
| snapshot_cancellation | 0 | True | True | 10760.255625005811 | unscored |
| snapshot_25_percent | 0 | True | True | 19441.27779197879 | unscored |
| snapshot_changed_one_transfer_route | 0 | True | True | 25762.45849998668 | unscored |
| snapshot_missed_connection | 0 | True | True | 31704.50875000097 | unscored |
| snapshot_handoff | 0 | True | True | 33906.971125048585 | unscored |
| snapshot_50_percent | 0 | True | True | 35925.03887496423 | unscored |

## Aggregate measurements

```json
{
  "attempted": 7,
  "correct": 7,
  "task_successes": 7,
  "technical_errors": 0,
  "audit_complete": 0,
  "invariant_counts": {
    "checked_execution.unverified": 7,
    "evidence_acceptance.unverified": 7,
    "repair_budget.unverified": 7,
    "price_asked_once.unverified": 7,
    "replayable.unverified": 7
  },
  "latency": {
    "count": 7,
    "median_ms": 25762.45849998668,
    "p95_ms": 35925.03887496423
  },
  "first_request": {
    "count": 1,
    "median_ms": 8643.882332951762,
    "p95_ms": 8643.882332951762
  },
  "warm_request": {
    "count": 6,
    "median_ms": 28733.483624993823,
    "p95_ms": 35925.03887496423
  },
  "judge_latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "stages": {
    "component": {
      "count": 7,
      "median_ms": 25762.230332940817,
      "p95_ms": 35924.76666602306
    }
  },
  "repeated_cases": 0,
  "decision_consistency": null,
  "quality_scored": 0,
  "quality_errors": 0,
  "quality_proxy": {},
  "tool_precision": {
    "count": 0,
    "mean": null
  },
  "tool_recall": {
    "count": 0,
    "mean": null
  },
  "parameter_accuracy": {
    "count": 0,
    "mean": null
  },
  "required_content_coverage": {
    "count": 0,
    "mean": null
  }
}
```
