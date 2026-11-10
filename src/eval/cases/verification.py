"""Provenance model and loader mirroring config/eval/verification.yaml."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from .base import ConfigModel, load_model


class VerifiedCase(ConfigModel):
    case_id: str
    correct: bool
    facts: dict[str, Any]
    latency_ms: float = Field(ge=0)


class Verification(ConfigModel):
    kind: Literal["verification"]
    version: Literal[1]
    timestamp: str
    scope: str
    case_document_sha256: str
    case_document_path: str
    original_case_document_sha256: str
    system_commit: str
    initialization_ms: float = Field(ge=0)
    checked: list[VerifiedCase]
    not_checked: list[str]
    performance_note: str


def load(path: Path = Path("config/eval/verification.yaml")) -> Verification:
    return load_model(path, Verification)
