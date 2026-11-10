# Refund evaluation

Scope: conversation. System: RefundSystemAdapter.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 1; correct: 1; task successes: 1; technical errors: 0.
Audit-complete runs: 1. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| dialogue_corrected_destination | 0 | True | True | 25711.183874984272 | scored |

## Aggregate measurements

```json
{
  "attempted": 1,
  "correct": 1,
  "task_successes": 1,
  "technical_errors": 0,
  "audit_complete": 1,
  "invariant_counts": {
    "checked_execution.passed": 1,
    "evidence_acceptance.passed": 1,
    "repair_budget.passed": 1,
    "price_asked_once.passed": 1,
    "replayable.passed": 1
  },
  "latency": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "first_request": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "warm_request": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "judge_latency": {
    "count": 1,
    "median_ms": 14966.248415992595,
    "p95_ms": 14966.248415992595
  },
  "stages": {},
  "repeated_cases": 0,
  "decision_consistency": null,
  "quality_scored": 1,
  "quality_errors": 0,
  "quality_proxy": {
    "relevance": {
      "count": 1,
      "mean": 5
    },
    "clarity": {
      "count": 1,
      "mean": 5
    },
    "coherence": {
      "count": 1,
      "mean": 5
    },
    "evidence_fidelity": {
      "count": 1,
      "mean": 5
    },
    "actionability": {
      "count": 1,
      "mean": 5
    }
  },
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
    "count": 1,
    "mean": 1.0
  }
}
```
