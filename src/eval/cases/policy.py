"""Model and loader mirroring config/eval/policy.yaml."""

from pathlib import Path
from typing import Literal

from .base import CaseDocument, load_model


class PolicyCases(CaseDocument):
    kind: Literal["policy"]
    description: str


def load(path: Path = Path("config/eval/policy.yaml")) -> PolicyCases:
    return load_model(path, PolicyCases)
