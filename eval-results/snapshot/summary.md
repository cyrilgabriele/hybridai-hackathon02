# Refund evaluation

Scope: component. System: FrameXSystem.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 5; correct: 5; task successes: 5; technical errors: 0.
Audit-complete runs: 0. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| snapshot_no_refund | 0 | True | True | 7181.430083932355 | unscored |
| snapshot_25_percent | 0 | True | True | 16679.95483300183 | unscored |
| snapshot_missed_connection | 0 | True | True | 22472.34654193744 | unscored |
| snapshot_handoff | 0 | True | True | 23302.227000007406 | unscored |
| snapshot_50_percent | 0 | True | True | 25629.560541943647 | unscored |

## Aggregate measurements

```json
{
  "attempted": 5,
  "correct": 5,
  "task_successes": 5,
  "technical_errors": 0,
  "audit_complete": 0,
  "invariant_counts": {
    "checked_execution.unverified": 5,
    "evidence_acceptance.unverified": 5,
    "repair_budget.unverified": 5,
    "price_asked_once.unverified": 5,
    "replayable.unverified": 5
  },
  "latency": {
    "count": 5,
    "median_ms": 22472.34654193744,
    "p95_ms": 25629.560541943647
  },
  "first_request": {
    "count": 1,
    "median_ms": 7181.430083932355,
    "p95_ms": 7181.430083932355
  },
  "warm_request": {
    "count": 4,
    "median_ms": 22887.286770972423,
    "p95_ms": 25629.560541943647
  },
  "judge_latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "stages": {
    "component": {
      "count": 5,
      "median_ms": 22472.289000055753,
      "p95_ms": 25629.37083293218
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
