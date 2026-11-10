"""Mirrored YAML models preserve gold values and reject ambiguous config input."""

import hashlib
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from eval.cases import dialogue, load_cases, policy, snapshot, verification
from eval.cases.base import read_yaml
from eval.discovery import write_discovery

CONFIG = Path(__file__).resolve().parents[2] / "config" / "eval"


@pytest.mark.parametrize("name,module", [("policy", policy), ("dialogue", dialogue), ("snapshot", snapshot)])
def test_mirrored_loaders_and_generic_loader_return_same_cases(name, module):
    path = CONFIG / f"{name}.yaml"
    document = module.load(path)
    assert [case.to_dict() for case in document.cases] == [case.to_dict() for case in load_cases(path)]
    assert document.kind == name
    assert document.cases


def test_money_strings_nulls_and_boolean_payout_are_preserved():
    cases = {case.id: case for case in policy.load(CONFIG / "policy.yaml").cases}
    below = cases["policy_60_chf_19.60"]
    assert below.request["price_chf"] == "19.60"
    assert below.expected["refundCHF"] == "4.90"
    assert below.expected["paidOut"] is False
    assert cases["policy_60_chf_None"].request["price_chf"] is None


@pytest.mark.parametrize("field_name", ["description", "version"])
def test_config_is_frozen_and_unknown_fields_are_rejected(tmp_path, field_name):
    document = policy.load(CONFIG / "policy.yaml")
    with pytest.raises(ValidationError, match="frozen"):
        setattr(document, field_name, "changed")
    path = tmp_path / "policy.yaml"
    path.write_text("kind: policy\nversion: 1\ndescription: test\ncases: []\ntypo: true\n")
    with pytest.raises(ValidationError, match="extra_forbidden"):
        policy.load(path)


def test_duplicate_keys_and_unsafe_yaml_tags_are_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("kind: policy\nkind: snapshot\n")
    with pytest.raises(ValueError, match="duplicate YAML key"):
        read_yaml(path)
    path.write_text("!!python/object/apply:os.system ['do not execute']")
    with pytest.raises(yaml.YAMLError):
        read_yaml(path)


def test_unquoted_iso_dates_stay_strings_but_money_must_be_quoted(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text("""kind: policy
version: 1
description: test
cases:
  - id: example
    request:
      day: 2026-11-07
      price_chf: '19.60'
    expected:
      decision: refund
      refundCHF: '4.90'
""")
    assert load_cases(path)[0].request["day"] == "2026-11-07"
    path.write_text(path.read_text().replace("price_chf: '19.60'", "price_chf: 19.60"))
    with pytest.raises(TypeError, match="quoted decimal string"):
        load_cases(path)


def test_discovery_serializes_through_snapshot_model_to_yaml(tmp_path):
    document = snapshot.load(CONFIG / "snapshot.yaml")
    path = tmp_path / "discovered.yaml"
    write_discovery(document.model_dump(), path)
    assert [case.to_dict() for case in snapshot.load(path).cases] == [case.to_dict() for case in document.cases]
    assert path.read_text().startswith("kind: snapshot\n")
    with pytest.raises(ValueError, match="yaml"):
        write_discovery(document.model_dump(), tmp_path / "discovered.json")


def test_verification_hash_follows_yaml_and_preserves_original_provenance():
    record = verification.load(CONFIG / "verification.yaml")
    assert record.case_document_path == "config/eval/snapshot.yaml"
    assert record.case_document_sha256 == hashlib.sha256((CONFIG / "snapshot.yaml").read_bytes()).hexdigest()
    assert record.original_case_document_sha256 != record.case_document_sha256
    cases = {case.id: case for case in snapshot.load(CONFIG / "snapshot.yaml").cases}
    assert {"snapshot_no_refund", "snapshot_25_percent", "snapshot_50_percent", "snapshot_handoff",
            "snapshot_missed_connection", "snapshot_cancellation", "snapshot_changed_one_transfer_route"}.issubset(
                {result.case_id for result in record.checked})
    for result in record.checked:
        assert result.correct
        assert result.case_id in cases
        expected_facts = {key: value for key, value in cases[result.case_id].expected.items() if key != "decision"}
        assert all(result.facts.get(key) == value for key, value in expected_facts.items())
