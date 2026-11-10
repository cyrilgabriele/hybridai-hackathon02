"""Component adapter; does not claim to test the passenger conversation pipeline."""

from __future__ import annotations

import json
import math
import time
from decimal import Decimal
from importlib.metadata import distribution
from pathlib import Path

from ontology import builder, emit
from runtime.client import Client
from runtime.query import binary
from runtime.session import Session

from ..contracts import Observation, SystemInput
from ..snapshot import fingerprint


class FrameXSystem:
    scope = "component"

    def __init__(self, workspace: Path | None = None, *, timeout: float = 900, load_timeout: float = 1800):
        if not all(math.isfinite(value) and value > 0 for value in (timeout, load_timeout)):
            raise ValueError("timeouts must be finite and positive")
        start = time.perf_counter()
        package = distribution("framex")
        direct = json.loads(package.read_text("direct_url.json") or "{}")
        commit = direct.get("vcs_info", {}).get("commit_id")
        receipt = Path(binary()).parent.parent / ".crates.toml"
        matches = commit in receipt.read_text() if commit and receipt.exists() else None
        if matches is False:
            raise ValueError("installed FrameX engine and client commits do not match")
        self.configuration = {"client_version": package.version, "client_commit": commit,
                              "engine_receipt_matches_client": matches, "timeout_seconds": timeout,
                              "load_timeout_seconds": load_timeout, "workspace": str(workspace) if workspace else None}
        self.session = Session(workspace, timeout=timeout, load_timeout=load_timeout) if workspace else None
        self.client = self.session.client if self.session else Client(binary(), request_timeout=timeout)
        self.sequence = 0
        try:
            self.workspace_hashes = fingerprint(workspace) if workspace else {}
            if not workspace:
                self.client.load("\n".join(path.read_text() for path in builder.ontology_files()))
        except BaseException:
            self.client.close()
            raise
        self.initialization_ms = (time.perf_counter() - start) * 1000

    def run(self, case: SystemInput) -> Observation:
        if case.snapshot and case.snapshot != self.workspace_hashes:
            raise ValueError("case snapshot does not match the loaded workspace")
        self.sequence += 1
        name = f"audit_{self.sequence}"
        request = case.request
        if "synthetic_delay" in request:
            if self.session:
                raise ValueError("synthetic policy cases require the isolated component adapter")
            delay = request["synthetic_delay"]
            if delay is None:
                source = f'{name}:DelayCheck. {name}[notMeasured -> "synthetic missing evidence"].'
            else:
                if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
                    raise ValueError("invalid synthetic delay")
                source = f"{name}[delayMeasured -> true; delayMinutes -> {delay}]."
        else:
            source = self._journey_source(name, request)
        price = request.get("price_chf")
        if price is not None:
            value = Decimal(price) * 100
            if not value.is_finite() or value < 0 or value != value.to_integral_value():
                raise ValueError("ticket price must be nonnegative whole Rappen")
            source += f"\n{name}[ticketPriceRappen -> {int(value)}]."
        start = time.perf_counter()
        self.client.add(source=source)
        facts = {}
        bindings = self.client.query(f"?- {name}[?Slot -> ?V].").get("bindings", [])
        for slot in ("refundStatus", "refundPercent", "refundRappen", "paidOut", "delayMeasured",
                     "delayMinutes", "plannedArrival", "actualArrival", "handOff"):
            rows = [row for row in bindings if row["Slot"] == slot]
            values = [json.loads(row["V"]) for row in rows]
            if len(values) > 1 and slot != "handOff":
                raise ValueError(f"conflicting bindings for {slot}")
            facts[slot] = values if slot == "handOff" else values[0] if values else None
        if not facts.pop("delayMeasured"):
            facts["delayMinutes"] = None
        rappen = facts.pop("refundRappen")
        facts["refundCHF"] = f"{Decimal(str(rappen)) / 100:.2f}" if rappen is not None else None
        status = facts["refundStatus"]
        decision = ("no_refund" if facts["paidOut"] is False else "refund") if status == "entitled" else (
            "no_refund" if status == "notEntitled" else "handoff")
        return Observation(decision, facts=facts,
                           stage_ms={"component": (time.perf_counter() - start) * 1000},
                           metadata={"scope": "component", "snapshot": self.workspace_hashes,
                                     "system_version": "framex-policy", "request_id": name,
                                     "configuration": self.configuration})

    @staticmethod
    def _journey_source(name: str, request: dict) -> str:
        for key in ("origin", "destination", "board_event"):
            if not isinstance(request[key], str) or not request[key].replace("_", "").isalnum():
                raise ValueError("invalid snapshot identifier")
        center = request["window_center"]
        transfer = request.get("transfer_seconds", 300)
        if type(center) is not int or type(transfer) is not int or transfer < 0:
            raise ValueError("invalid time arguments")
        # Generated from validated scalar fields; no executable text is accepted.
        source = (f'{name}_case:RefundCase[origin -> {request["origin"]}; '
                  f'destination -> {request["destination"]}; onDay -> {emit.required_literal(request["day"], "String")}; '
                  f'windowFrom -> {center - 1800}; windowTo -> {center + 1800}; transferSeconds -> {transfer}].\n'
                  f'{name}:DelayCheck[checkOf -> {name}_case; plannedBoard -> {request["board_event"]}].')
        return source

    def close(self) -> None:
        self.client.close()
