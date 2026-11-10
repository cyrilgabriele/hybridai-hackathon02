"""Start the fact-safe refund assistant: `uv run python src/refund_chat.py`."""

from __future__ import annotations

import argparse

from pipeline.assistant import build_assistant
from ui.app import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=7860, help="local port of the app")
    args = parser.parse_args()
    # Each decision runs in its own engine of about 2 GB, so one at a time.
    build_app(build_assistant()).queue(default_concurrency_limit=1).launch(server_name="127.0.0.1", server_port=args.port)


if __name__ == "__main__":
    main()
