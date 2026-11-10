# Refund evaluation

Scope: conversation. System: RefundSystemAdapter.
Quality scores are automated proxies, not measured user satisfaction.

Attempted: 17; correct: 17; task successes: 17; technical errors: 0.
Audit-complete runs: 17. Missing instrumentation is unverified.

| Case | Repeat | Correct | Task success | Latency ms | Quality |
|---|---:|---|---|---:|---|
| snapshot_no_refund | 0 | True | True | 19242.463249946013 | scored |
| snapshot_cancellation | 0 | True | True | 13544.953166041523 | scored |
| snapshot_25_percent | 0 | True | True | 19525.221958989277 | scored |
| snapshot_changed_one_transfer_route | 0 | True | True | 17625.878707971424 | scored |
| snapshot_missed_connection | 0 | True | True | 16077.193959034048 | scored |
| snapshot_handoff | 0 | True | True | 20850.753249949776 | scored |
| snapshot_50_percent | 0 | True | True | 10901.472709025256 | scored |
| snapshot_25_percent_chf_19_60 | 0 | True | True | 25150.176000082865 | scored |
| snapshot_25_percent_chf_20_00 | 0 | True | True | 15933.601792086847 | scored |
| snapshot_25_percent_chf_20_02 | 0 | True | True | 16297.65312501695 | scored |
| snapshot_25_percent_chf_24_00 | 0 | True | True | 18622.34554195311 | scored |
| snapshot_50_percent_chf_9_80 | 0 | True | True | 17379.37266600784 | scored |
| snapshot_50_percent_chf_10_00 | 0 | True | True | 15081.866708002053 | scored |
| snapshot_50_percent_chf_10_01 | 0 | True | True | 11709.950958029367 | scored |
| snapshot_50_percent_chf_12_00 | 0 | True | True | 10818.596833036281 | scored |
| snapshot_missing_price | 0 | True | True | 20076.219749986194 | scored |
| snapshot_unsupported_day | 0 | True | True | 16587.544749956578 | scored |

## Aggregate measurements

```json
{
  "attempted": 17,
  "correct": 17,
  "task_successes": 17,
  "technical_errors": 0,
  "audit_complete": 17,
  "invariant_counts": {
    "checked_execution.passed": 17,
    "evidence_acceptance.passed": 17,
    "repair_budget.passed": 17,
    "price_asked_once.passed": 17,
    "replayable.passed": 17
  },
  "latency": {
    "count": 17,
    "median_ms": 16587.544749956578,
    "p95_ms": 25150.176000082865
  },
  "first_request": {
    "count": 1,
    "median_ms": 19242.463249946013,
    "p95_ms": 19242.463249946013
  },
  "warm_request": {
    "count": 16,
    "median_ms": 16442.598937486764,
    "p95_ms": 25150.176000082865
  },
  "judge_latency": {
    "count": 17,
    "median_ms": 15199.908667011186,
    "p95_ms": 34011.8728330126
  },
  "stages": {
    "end_to_end": {
      "count": 17,
      "median_ms": 16583.280249964446,
      "p95_ms": 25146.874458063394
    },
    "model_extraction": {
      "count": 17,
      "median_ms": 11562.478333944455,
      "p95_ms": 18611.527167027816
    },
    "model_generation": {
      "count": 17,
      "median_ms": 1530.8255829149857,
      "p95_ms": 6366.724834078923
    },
    "engine": {
      "count": 17,
      "median_ms": 1303.4981250530109,
      "p95_ms": 4879.159958101809
    }
  },
  "repeated_cases": 0,
  "decision_consistency": null,
  "quality_scored": 17,
  "quality_errors": 0,
  "quality_proxy": {
    "relevance": {
      "count": 17,
      "mean": 5
    },
    "clarity": {
      "count": 17,
      "mean": 4.9411764705882355
    },
    "coherence": {
      "count": 17,
      "mean": 4.9411764705882355
    },
    "evidence_fidelity": {
      "count": 17,
      "mean": 4.9411764705882355
    },
    "actionability": {
      "count": 17,
      "mean": 3.764705882352941
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
    "count": 17,
    "mean": 1.0
  }
}
```
