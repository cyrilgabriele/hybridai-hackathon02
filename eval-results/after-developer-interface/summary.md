# Refund evaluation

Scope: component. System: FrameXSystem.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 5; correct: 5; task successes: 5; technical errors: 0.
Audit-complete runs: 0. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| snapshot_no_refund | 0 | True | True | 7482.493708957918 | unscored |
| snapshot_25_percent | 0 | True | True | 16968.00762496423 | unscored |
| snapshot_missed_connection | 0 | True | True | 22365.072958986275 | unscored |
| snapshot_handoff | 0 | True | True | 23798.697707941756 | unscored |
| snapshot_50_percent | 0 | True | True | 25701.123625040054 | unscored |

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
    "median_ms": 22365.072958986275,
    "p95_ms": 25701.123625040054
  },
  "first_request": {
    "count": 1,
    "median_ms": 7482.493708957918,
    "p95_ms": 7482.493708957918
  },
  "warm_request": {
    "count": 4,
    "median_ms": 23081.885333464015,
    "p95_ms": 25701.123625040054
  },
  "judge_latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "stages": {
    "component": {
      "count": 5,
      "median_ms": 22364.837625063956,
      "p95_ms": 25700.87749999948
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
