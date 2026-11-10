"""Independent boundary and invariant checks must catch plausible but wrong results."""

import pytest

from eval.contracts import Case, Observation
from eval.metrics import evaluate, invariants, tool_metrics
from eval.policy import expected_refund


@pytest.mark.parametrize("delay,percent", [(0, 0), (59, 0), (60, 25), (119, 25), (120, 50)])
def test_thresholds(delay, percent):
    assert expected_refund(delay, "40.00")["refundPercent"] == percent


def test_rounding_does_not_create_payout_entitlement():
    expected = expected_refund(60, "19.99")
    assert expected["refundCHF"] == "5.00"
    assert expected["paidOut"] is False
    assert expected["decision"] == "no_refund"
    assert expected["refundStatus"] == "entitled"
    assert expected_refund(60, "20.00")["paidOut"] is True
    assert expected_refund(120, "10.01")["refundCHF"] == "5.01"
    assert expected_refund(None)["decision"] == "handoff"


@pytest.mark.parametrize("price", ["NaN", "Infinity", "-1", "2.001"])
def test_invalid_prices_are_not_silently_normalized(price):
    with pytest.raises(ValueError):
        expected_refund(60, price)


def test_duplicate_unnecessary_calls_reduce_precision():
    events = [{"kind": "execute", "name": "lookup", "arguments": {"id": 1}}] * 2
    scores = tool_metrics(events, [{"name": "lookup", "arguments": {"id": 1}}])
    assert scores == {"tool_precision": 0.5, "tool_recall": 1, "parameter_accuracy": 1}
    assert tool_metrics(events, [])["tool_precision"] == 0
    assert tool_metrics(events, None)["tool_precision"] is None


def test_validation_must_precede_execution_with_matching_arguments():
    validate = {"kind": "validate", "call_id": "a", "approved": True,
                "name": "lookup", "arguments": {"id": 1}}
    execute = {**validate, "kind": "execute"}
    result = Observation("refund", events=[execute, validate], coverage=["checked_execution"])
    assert invariants(result)["checked_execution"] == "failed"
    result.events = [validate, execute]
    assert invariants(result)["checked_execution"] == "passed"
    result.events[-1] = {**execute, "arguments": {"id": 2}}
    assert invariants(result)["checked_execution"] == "failed"
    assert invariants(Observation("refund"))["checked_execution"] == "unverified"


def test_acceptance_requires_real_evidence_references_and_repair_is_bounded():
    result = Observation("refund", events=[{"kind": "accept", "evidence": ["absent"]}],
                         coverage=["evidence_acceptance"])
    assert invariants(result)["evidence_acceptance"] == "failed"
    result.metadata["evidence"] = {"absent": {"source": "snapshot event", "value": 60}}
    assert invariants(result)["evidence_acceptance"] == "passed"
    result.events += [{"kind": "repair"}, {"kind": "repair"}]
    assert invariants(result)["repair_budget"] == "failed"


def test_fabricated_quote_and_handoff_verdict_are_failures():
    case = Case("q", {}, {"decision": "question"}, messages=[{"role": "user", "content": "From Bern."}])
    result = Observation("question", events=[{"kind": "slot", "accepted": True,
                                               "quote": "Basel", "message_index": 0}])
    assert evaluate(case, result, scope="conversation")["correct"] is False
    result = Observation("handoff", facts={"refundPercent": 25})
    case.expected = {"decision": "handoff"}
    assert not evaluate(case, result, scope="conversation")["correct"]


def test_transport_decision_cannot_be_overridden_by_facts():
    case = Case("wrong", {}, {"decision": "refund"})
    result = Observation("no_refund", facts={"decision": "refund"})
    assert not evaluate(case, result, scope="component")["correct"]


def test_required_number_does_not_match_inside_another_number():
    case = Case("wrong_percent", {}, {"decision": "refund"}, must_say=["25"])
    result = Observation("refund", "You get 125 percent.")
    assert evaluate(case, result, scope="conversation")["required_content_coverage"] == 0


def test_extraction_and_phrasing_have_separate_repair_budgets():
    result = Observation("refund", events=[{"kind": "repair", "scope_id": "slots_turn_1"},
                                            {"kind": "repair", "scope_id": "reply_turn_1"}],
                         coverage=["repair_budget"])
    assert invariants(result)["repair_budget"] == "passed"
    result.events.append({"kind": "repair", "scope_id": "reply_turn_1"})
    assert invariants(result)["repair_budget"] == "failed"
