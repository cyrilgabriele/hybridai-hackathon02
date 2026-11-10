"""Strict config documents and safe YAML I/O shared by the mirrored loaders."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .models import Case

Model = TypeVar("Model", bound=BaseModel)


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys rather than silently changing a gold answer."""

    def __init__(self, stream):
        super().__init__(stream)
        # Keep dates as strings without modifying PyYAML's global resolvers.
        self.yaml_implicit_resolvers = {
            key: [(tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:timestamp"]
            for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
        }

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key, value in self.construct_pairs(node, deep=deep):
            if key in result:
                raise ValueError(f"duplicate YAML key: {key!r}")
            result[key] = value
        return result


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CaseDocument(ConfigModel):
    version: Literal[1]
    cases: list[Case]

    @field_validator("cases", mode="before")
    @classmethod
    def parse_cases(cls, values: Any) -> list[Case]:
        if not isinstance(values, list):
            raise TypeError("cases must be a list")
        return [value if isinstance(value, Case) else Case.from_dict(value) for value in values]

    @model_validator(mode="after")
    def unique_ids(self) -> CaseDocument:
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("duplicate case IDs")
        return self


def read_yaml(path: Path) -> dict[str, Any]:
    if path.suffix not in {".yaml", ".yml"}:
        raise ValueError("case config must be a .yaml or .yml file")
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(document, dict):
        raise TypeError("YAML config must be an object")
    return document


def load_model(path: Path, model: type[Model]) -> Model:
    return model.model_validate(read_yaml(path))


def write_model(document: BaseModel, path: Path) -> None:
    if path.suffix not in {".yaml", ".yml"}:
        raise ValueError("case config output must be a .yaml or .yml file")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = document.model_dump(mode="json", exclude_defaults=True)
    cases = data.pop("cases", None)
    data = {"kind": data.pop("kind"), "version": data.pop("version"), **data}
    if cases is not None:
        data["cases"] = cases
    path.write_text(yaml.safe_dump(data, allow_unicode=True,
                                   sort_keys=False, width=100), encoding="utf-8")
