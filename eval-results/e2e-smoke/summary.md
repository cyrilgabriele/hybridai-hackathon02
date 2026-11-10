# Refund evaluation

Scope: conversation. System: RefundSystemAdapter.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 1; correct: 1; task successes: 1; technical errors: 0.
Audit-complete runs: 1. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| snapshot_no_refund | 0 | True | True | 14970.8586250199 | scored |

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
    "count": 1,
    "median_ms": 14970.8586250199,
    "p95_ms": 14970.8586250199
  },
  "first_request": {
    "count": 1,
    "median_ms": 14970.8586250199,
    "p95_ms": 14970.8586250199
  },
  "warm_request": {
    "count": 0,
    "median_ms": null,
    "p95_ms": null
  },
  "judge_latency": {
    "count": 1,
    "median_ms": 16016.148624941707,
    "p95_ms": 16016.148624941707
  },
  "stages": {
    "end_to_end": {
      "count": 1,
      "median_ms": 14957.937125000171,
      "p95_ms": 14957.937125000171
    },
    "model_extraction": {
      "count": 1,
      "median_ms": 12131.471166969277,
      "p95_ms": 12131.471166969277
    },
    "model_generation": {
      "count": 1,
      "median_ms": 1671.1542080156505,
      "p95_ms": 1671.1542080156505
    },
    "engine": {
      "count": 1,
      "median_ms": 1152.965542045422,
      "p95_ms": 1152.965542045422
    }
  },
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
      "mean": 4
    },
    "coherence": {
      "count": 1,
      "mean": 4
    },
    "evidence_fidelity": {
      "count": 1,
      "mean": 4
    },
    "actionability": {
      "count": 1,
      "mean": 3
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
