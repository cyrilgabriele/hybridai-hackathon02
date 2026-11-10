# Refund evaluation

Scope: conversation. System: RefundSystemAdapter.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 9; correct: 9; task successes: 9; technical errors: 2.
Audit-complete runs: 3. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| dialogue_missing_origin | 0 | True | True | 9437.164584058337 | scored |
| dialogue_ambiguous_station | 0 | True | True | 8614.70591602847 | scored |
| dialogue_wrong_day | 0 | True | True | 11768.26316700317 | scored |
| dialogue_injected_rule | 0 | True | True | 7299.616292002611 | scored |
| dialogue_unfounded_quote | 0 | True | True | 1228.3984170062467 | scored |
| dialogue_model_timeout | 0 | True | True | 2.004791982471943 | unscored |
| dialogue_tool_timeout | 0 | True | True | 11985.599334002472 | unscored |
| dialogue_repair_exhausted | 0 | True | True | 1143.7474580015987 | scored |
| dialogue_corrected_destination | 0 | True | True | 25897.126708063297 | scored |

## Aggregate measurements

```json
{
  "attempted": 9,
  "correct": 9,
  "task_successes": 9,
  "technical_errors": 2,
  "audit_complete": 3,
  "invariant_counts": {
    "checked_execution.unverified": 6,
    "evidence_acceptance.passed": 6,
    "repair_budget.passed": 9,
    "price_asked_once.passed": 9,
    "replayable.passed": 9,
    "checked_execution.passed": 3,
    "evidence_acceptance.unverified": 3
  },
  "latency": {
    "count": 4,
    "median_ms": 9025.935250043403,
    "p95_ms": 11768.26316700317
  },
  "first_request": {
    "count": 1,
    "median_ms": 9437.164584058337,
    "p95_ms": 9437.164584058337
  },
  "warm_request": {
    "count": 3,
    "median_ms": 8614.70591602847,
    "p95_ms": 11768.26316700317
  },
  "judge_latency": {
    "count": 7,
    "median_ms": 9079.623500001617,
    "p95_ms": 11991.62491702009
  },
  "stages": {
    "end_to_end": {
      "count": 4,
      "median_ms": 9019.090750080068,
      "p95_ms": 11762.181165977381
    },
    "model_extraction": {
      "count": 4,
      "median_ms": 6808.84233355755,
      "p95_ms": 8255.208000075072
    },
    "model_generation": {
      "count": 4,
      "median_ms": 1402.0442715263925,
      "p95_ms": 5049.490459030494
    },
    "engine": {
      "count": 4,
      "median_ms": 0.0,
      "p95_ms": 69.45108401123434
    }
  },
  "repeated_cases": 0,
  "decision_consistency": null,
  "quality_scored": 7,
  "quality_errors": 0,
  "quality_proxy": {
    "relevance": {
      "count": 7,
      "mean": 4.571428571428571
    },
    "clarity": {
      "count": 7,
      "mean": 4.857142857142857
    },
    "coherence": {
      "count": 7,
      "mean": 4.571428571428571
    },
    "evidence_fidelity": {
      "count": 7,
      "mean": 4.571428571428571
    },
    "actionability": {
      "count": 7,
      "mean": 4.571428571428571
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
    "count": 2,
    "mean": 1.0
  }
}
```
