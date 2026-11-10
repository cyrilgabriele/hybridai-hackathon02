"""Model and loader mirroring config/eval/dialogue.yaml."""

from pathlib import Path
from typing import Literal

from .base import CaseDocument, load_model


class DialogueCases(CaseDocument):
    kind: Literal["dialogue"]
    description: str


def load(path: Path = Path("config/eval/dialogue.yaml")) -> DialogueCases:
    return load_model(path, DialogueCases)
