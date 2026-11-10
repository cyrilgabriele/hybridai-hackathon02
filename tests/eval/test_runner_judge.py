"""No network calls: mock the judge boundary and exercise reporting failures."""

import json
from types import SimpleNamespace

import pytest

from eval.adapters.openai_judge import DIMENSIONS, OpenAIJudge
from eval.adapters.saved import SavedRuns
from eval.cases import load_cases
from eval.contracts import Case, Observation
from eval.runner import durations, run_cases, write_report


class System:
    scope = "conversation"

    def __init__(self):
        self.closed = False

    def run(self, request):
        assert not hasattr(request, "expected")
        assert not hasattr(request, "evidence")
        if request.id == "broken":
            raise RuntimeError("sensitive exception content must not be reported")
        return Observation("refund", "25 % refund", stage_ms={"model": 2.0})

    def close(self):
        self.closed = True


def test_failed_attempts_stay_in_denominator_and_missing_data_is_not_perfect(tmp_path):
    system = System()
    cases = [Case("ok", {}, {"decision": "refund"}, must_say=["25"]), Case("broken", {}, {"decision": "refund"})]
    report = run_cases(system, cases, repeats=2)
    assert system.closed
    assert report["summary"]["attempted"] == 4
    assert report["summary"]["correct"] == 2
    assert report["summary"]["technical_errors"] == 2
    assert report["summary"]["tool_precision"]["count"] == 0
    assert report["summary"]["quality_scored"] == 0
    write_report(report, tmp_path)
    assert "sensitive exception" not in (tmp_path / "results.json").read_text()
    assert (tmp_path / "summary.md").exists()


def test_nearest_rank_percentile_and_empty_samples():
    assert durations(list(range(1, 21))) == {"count": 20, "median_ms": 10.5, "p95_ms": 19}
    assert durations([])["median_ms"] is None


def test_saved_run_does_not_benchmark_json_replay(tmp_path):
    path = tmp_path / "saved.json"
    path.write_text(json.dumps({"rows": [{"case_id": "x", "observation": {"decision": "refund"}}]}))
    report = run_cases(SavedRuns(path), [Case("x", {}, {"decision": "refund"})])
    assert report["summary"]["latency"]["count"] == 0
    assert report["rows"][0]["replayed"] is True


def judge_client(ratings, status="completed"):
    def create(**kwargs):
        assert kwargs["text"]["format"]["strict"] is True
        assert kwargs["store"] is False
        return SimpleNamespace(status=status, output_text=json.dumps(ratings), id="mock",
                               usage=None)
    return SimpleNamespace(responses=SimpleNamespace(create=create))


def test_judge_requires_scores_reasons_and_verbatim_response_evidence():
    ratings = {name: {"score": 4, "reason": "Addresses the question", "excerpt": "25 %"}
               for name in DIMENSIONS}
    case = Case("x", {}, {"decision": "refund"})
    result = Observation("refund", "25 % refund")
    judge = OpenAIJudge("explicit-model", judge_client(ratings))
    assert judge.score(case, result)["ratings"]["clarity"]["score"] == 4
    ratings["clarity"]["excerpt"] = "not in the reply"
    with pytest.raises(ValueError, match="unsupported excerpt"):
        judge.score(case, result)
    ratings["clarity"]["excerpt"] = "25 %"
    ratings["clarity"]["score"] = True
    with pytest.raises(ValueError):
        judge.score(case, result)
    with pytest.raises(ValueError, match="incomplete"):
        OpenAIJudge("model", judge_client(ratings, "incomplete")).score(case, result)


def test_judge_error_does_not_erase_correctness():
    class BrokenJudge:
        def score(self, case, observation):
            raise TimeoutError("provider failure")
    report = run_cases(System(), [Case("ok", {}, {"decision": "refund"})], judge=BrokenJudge())
    assert report["summary"]["correct"] == 1
    assert report["summary"]["quality_errors"] == 1


def test_system_cannot_downgrade_conversation_checks_to_component_scope():
    class MislabelledSystem(System):
        def run(self, request):
            return Observation("refund", metadata={"scope": "component"})
    report = run_cases(MislabelledSystem(), [Case("ok", {}, {"decision": "refund"})])
    assert report["rows"][0]["scope"] == "conversation"
    assert report["summary"]["task_successes"] == 0


def test_bad_case_documents_and_observations_are_rejected(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(json.dumps({"kind": "policy", "version": 1, "description": "test", "cases": [
        {"id": "x", "request": {}, "expected": {"decision": "refund"}},
        {"id": "x", "request": {}, "expected": {"decision": "refund"}}]}))
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)
    with pytest.raises(ValueError, match="durations"):
        Observation.from_dict({"decision": "refund", "stage_ms": {"model": float("nan")}})
