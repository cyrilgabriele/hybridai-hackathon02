"""Model and loader mirroring config/eval/snapshot.yaml."""

from pathlib import Path
from typing import Literal

from pydantic import Field

from .base import CaseDocument, load_model


class SnapshotCases(CaseDocument):
    kind: Literal["snapshot"]
    created: str
    snapshot: dict[str, str]
    candidate_limit: int = Field(gt=0)
    examined: int = Field(ge=0)
    coverage: list[str]
    unavailable: list[str]
    verification: str


def load(path: Path = Path("config/eval/snapshot.yaml")) -> SnapshotCases:
    return load_model(path, SnapshotCases)
