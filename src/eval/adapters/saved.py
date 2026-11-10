"""Normalize saved observations without timing replay as agent performance."""

import json
from pathlib import Path

from ..contracts import Observation, SystemInput


class SavedRuns:
    scope = "replay"

    def __init__(self, path: Path):
        raw = json.loads(path.read_text())
        self.rows = {}
        for row in raw["rows"]:
            key = (row["case_id"], row.get("repetition", 0))
            if key in self.rows:
                raise ValueError("duplicate recorded attempt")
            self.rows[key] = row
        self.repetitions: dict[str, int] = {}

    def run(self, case: SystemInput) -> Observation:
        repeat = self.repetitions.get(case.id, 0)
        self.repetitions[case.id] = repeat + 1
        row = self.rows[(case.id, repeat)]
        result = Observation.from_dict(row["observation"])
        if row.get("latency_ms") is not None:
            result.stage_ms["end_to_end"] = row["latency_ms"]
        result.metadata["scope"] = row.get("scope", "conversation")
        return result

    def close(self) -> None:
        pass
