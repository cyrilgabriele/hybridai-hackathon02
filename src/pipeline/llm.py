"""GPT-5 mini through the official OpenAI client.

The key comes from the environment (`OPENAI_API_KEY`, or a `.env` file in the
repository root) and is never logged. Every answer is recorded in
`model-answers/` and replayed for an identical request, so each answer is dated
and a demo still runs after the hackathon key has expired. Set
`REFUND_MODEL_REFRESH=1` to ask the model again.

Run this file alone for a one-call smoke test:

    uv run python src/pipeline/llm.py
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared import ReasoningEffort

ROOT = Path(__file__).resolve().parents[2]
MODEL = "gpt-5-mini"
ANSWERS = ROOT / "model-answers"
TIMEOUT_SECONDS = 60.0


class ModelCallFailed(RuntimeError):
    """The call itself failed: a technical error, never an unclear answer."""


@dataclass(frozen=True)
class ModelAnswer:
    """One reply. `data` is None when the reply was not a JSON object."""

    data: dict | None
    raw: str
    mode: str  # "live" or "replay"
    recorded_at: str
    seconds: float
    usage: dict = field(default_factory=dict)


def _parse(raw: str) -> dict | None:
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


class LanguageModel:
    """One JSON-returning chat call, with record and replay."""

    def __init__(self, store: Path = ANSWERS, client: OpenAI | None = None, *, refresh: bool = False):
        load_dotenv(ROOT / ".env", override=False)
        self.refresh = refresh
        self.store = store
        self._client = client

    def _openai(self) -> OpenAI:
        if self._client is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise ModelCallFailed("OPENAI_API_KEY is not set")
            self._client = OpenAI(timeout=TIMEOUT_SECONDS, max_retries=1)
        return self._client

    def ask_json(self, system: str, user: str, *, effort: ReasoningEffort = "low") -> ModelAnswer:
        """Ask once; replay an identical earlier request instead of calling."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        identity = json.dumps([MODEL, messages], ensure_ascii=False, sort_keys=True)
        path = self.store / f"{hashlib.sha256(identity.encode()).hexdigest()[:24]}.json"
        if not self.refresh and path.exists() and os.environ.get("REFUND_MODEL_REFRESH") != "1":
            stored = json.loads(path.read_text(encoding="utf-8"))
            return ModelAnswer(_parse(stored["raw"]), stored["raw"], "replay", stored["recorded_at"], 0.0, stored.get("usage", {}))
        started = time.monotonic()
        try:
            response = self._openai().chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                reasoning_effort=effort,
            )
        except OpenAIError as exc:
            raise ModelCallFailed(type(exc).__name__) from None
        raw = response.choices[0].message.content or ""
        recorded_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.store.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"recorded_at": recorded_at, "model": MODEL, "messages": messages, "raw": raw,
                        "usage": response.usage.model_dump() if response.usage else {}},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        return ModelAnswer(_parse(raw), raw, "live", recorded_at, time.monotonic() - started,
                           response.usage.model_dump() if response.usage else {})


if __name__ == "__main__":
    model = LanguageModel()
    key = os.environ.get("OPENAI_API_KEY", "")
    print(f"model: {MODEL}; key is {'set' if key else 'NOT set'} ({len(key)} characters)")
    answer = model.ask_json('Answer as JSON {"capital": ...}.', "What is the capital of Switzerland?")
    print(f"{answer.mode} in {answer.seconds:.1f}s: {answer.data}")
