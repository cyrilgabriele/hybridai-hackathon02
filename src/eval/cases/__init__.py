"""Load scenario definitions from YAML through their mirrored config models."""

from pathlib import Path

from .base import read_yaml
from .dialogue import DialogueCases
from .models import Case
from .policy import PolicyCases
from .snapshot import SnapshotCases

DOCUMENT_MODELS = {"policy": PolicyCases, "dialogue": DialogueCases, "snapshot": SnapshotCases}


def load_cases(path: Path) -> list[Case]:
    document = read_yaml(path)
    kind = document.get("kind")
    if not isinstance(kind, str) or kind not in DOCUMENT_MODELS:
        raise ValueError("case document kind must be policy, dialogue or snapshot")
    return DOCUMENT_MODELS[kind].model_validate(document).cases
