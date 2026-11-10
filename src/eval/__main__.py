"""CLI composition root: adapters are explicit; importing the core never calls a model."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

from .cases import load_cases
from .discovery import discover, write_discovery
from .runner import run_cases, write_report


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Independent refund evaluation")
    commands = root.add_subparsers(dest="command", required=True)
    discovery = commands.add_parser("discover", help="freeze independently calculated snapshot cases")
    discovery.add_argument("--workspace", type=Path, default=Path("fx"))
    discovery.add_argument("--output", type=Path, required=True, help="output YAML case config (.yaml or .yml)")
    discovery.add_argument("--limit", type=int, default=250)
    run = commands.add_parser("run", help="run a component/system adapter or score saved observations")
    run.add_argument("--cases", type=Path, required=True, help="YAML case config, e.g. config/eval/snapshot.yaml")
    run.add_argument("--output", type=Path, required=True)
    adapters = run.add_mutually_exclusive_group(required=True)
    adapters.add_argument("--framex", action="store_true", help="component tests; no chat/LLM is implied")
    adapters.add_argument("--adapter", help="module:factory returning SystemPort; called without arguments")
    adapters.add_argument("--saved", type=Path)
    run.add_argument("--workspace", type=Path, help="omit for isolated synthetic FrameX policy cases")
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--case", action="append", dest="case_ids", help="select a case ID; repeat to select several")
    run.add_argument("--timeout", type=float, default=900, help="FrameX request timeout in seconds")
    run.add_argument("--load-timeout", type=float, default=1800, help="FrameX bulk-load request timeout")
    run.add_argument("--judge", choices=["openai"])
    run.add_argument("--judge-model")
    run.add_argument("--client-factory", help="optional module:factory supplying the team's OpenAI client")
    return root


def factory(spec: str):
    module, separator, name = spec.partition(":")
    if not separator:
        raise ValueError("adapter factory must be module:attribute")
    return getattr(importlib.import_module(module), name)()


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "discover":
            if args.limit < 1:
                raise ValueError("limit must be positive")
            document = discover(args.workspace, limit=args.limit)
            write_discovery(document, args.output)
            print(json.dumps({key: document[key] for key in ("coverage", "unavailable", "examined")}))
            return 0
        cases = load_cases(args.cases)
        if args.case_ids:
            unknown = set(args.case_ids) - {case.id for case in cases}
            if unknown:
                raise ValueError("unknown case IDs")
            cases = [case for case in cases if case.id in args.case_ids]
        if args.repeats < 1:
            raise ValueError("repeats must be positive")
        judge = None
        if args.judge:
            from dotenv import load_dotenv

            from .adapters.openai_judge import OpenAIJudge
            load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
            model = args.judge_model or os.environ.get("OPENAI_EVAL_MODEL")
            if not model:
                raise ValueError("--judge-model or OPENAI_EVAL_MODEL is required")
            judge = OpenAIJudge(model, factory(args.client_factory) if args.client_factory else None)
        if args.framex:
            from .adapters.framex_system import FrameXSystem
            print("Loading FrameX component workspace...", file=sys.stderr, flush=True)
            system = FrameXSystem(args.workspace, timeout=args.timeout, load_timeout=args.load_timeout)
        elif args.saved:
            from .adapters.saved import SavedRuns
            system = SavedRuns(args.saved)
        else:
            system = factory(args.adapter)
        report = run_cases(system, cases, repeats=args.repeats, judge=judge,
                           progress=lambda message: print(message, file=sys.stderr, flush=True))
        report["case_document"] = str(args.cases)
        write_report(report, args.output)
        print(json.dumps(report["summary"], indent=2))
        return int(report["summary"]["correct"] != report["summary"]["attempted"])
    except Exception as exc:  # noqa: BLE001 -- do not leak provider credentials through exception messages
        print(f"evaluation could not run ({type(exc).__name__}); check arguments, inputs and adapter configuration")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
