"""Freeze independently calculated snapshot cases; do not label discovery as a system run."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .cases.base import write_model
from .cases.snapshot import SnapshotCases
from .contracts import Case
from .policy import expected_refund
from .snapshot import Snapshot, fingerprint


def _case(snapshot: Snapshot, request: dict, category: str, hashes: dict[str, str]) -> Case:
    evidence = snapshot.evaluate(request)
    delay = evidence["delayMinutes"]
    expected = expected_refund(delay, request.get("price_chf"))
    expected["delayMinutes"] = delay
    if delay is not None:
        expected.update({key: evidence[key] for key in ("plannedArrival", "actualArrival")})
    source = snapshot.names.get(request["origin"], request["origin"])
    destination = snapshot.names.get(request["destination"], request["destination"])
    clock = datetime.fromtimestamp(request["window_center"], ZoneInfo("Europe/Zurich")).strftime("%H:%M")
    trip = snapshot.trips[snapshot.events[request["board_event"]]["ofTrip"]]["tripRef"]
    price_text = f" My ticket cost CHF {request['price_chf']}." if request.get("price_chf") is not None else ""
    text = (f"I travelled from {source} to {destination} on {request['day']} at {clock}, "
            f"train {trip}.{price_text} Can I get compensation?")
    must_say = [source, destination]
    if delay is None:
        must_say = ["customer service"]
    else:
        must_say += [str(delay), "60" if delay < 60 else str(expected["refundPercent"])]
        if expected["paidOut"] is False:
            must_say += ["5"]
        if request.get("price_chf") is None and delay >= 60:
            must_say += ["5", "price"]
    return Case(id=f"snapshot_{category}", request=request, expected=expected,
                tags=["snapshot", category], messages=[{"role": "user", "content": text}],
                must_say=must_say, snapshot=hashes,
                evidence={**evidence, "source": source, "destination": destination,
                          "trip_ref": trip, "ticket_price_source": "synthetic passenger statement",
                          "oracle": "independent enumeration; not production-rule output",
                          "search_limits_seconds": {"start_wait": 10800, "change_wait": 3600, "journey": 14400}})


def discover(workspace: Path, *, limit: int = 250) -> dict:
    snapshot = Snapshot(workspace)
    hashes = fingerprint(workspace)
    # Seed difficult cancellation cases, then search deterministically for other categories.
    seeds = [
        ("ev_18118061f3f3cadb1546dfb62e066586", "sp_8507483"),
        ("ev_0d6ee0b2810d1e861464dc526a0054b0", "sp_8503000"),
        ("ev_798c297609cdadf24c3b463845c5b829", "sp_8501601"),
    ]
    candidates = [(board, dest) for board, dest in seeds if board in snapshot.events and dest in snapshot.names]
    for board, event in snapshot.events.items():
        if event.get("passThrough") is not False or "scheduledDepartureEpoch" not in event:
            continue
        day = snapshot.trips[event["ofTrip"]].get("observedOn")
        if day != "2026-11-07":
            continue
        later = snapshot.later(board, False, day)
        for finish in later[-2:]:
            end = snapshot.events[finish]
            if "scheduledArrivalEpoch" not in end:
                continue
            missing = event.get("cancelled") is False and "arrivalEpoch" not in end
            delayed = end.get("arrivalEpoch", 0) - end["scheduledArrivalEpoch"] >= 3600
            if event.get("cancelled") is True or missing or delayed:
                candidates.append((board, end["atStopPoint"]))
    candidates = [*candidates[:len(seeds)], *_missed_connection_candidates(snapshot), *candidates[len(seeds):]]
    selected: dict[str, Case] = {}
    examined = 0
    for board, destination in dict.fromkeys(candidates):
        if examined >= limit:
            break
        start = snapshot.events[board]
        if start["atStopPoint"] == destination:
            continue
        request = {"origin": start["atStopPoint"], "destination": destination,
                   "board_event": board, "day": "2026-11-07",
                   "window_center": start["scheduledDepartureEpoch"], "transfer_seconds": 300,
                   "price_chf": "40.00"}
        case = _case(snapshot, request, "candidate", hashes)
        examined += 1
        if not case.evidence["offered"]:
            continue
        delay = case.evidence["delayMinutes"]
        band = "handoff" if delay is None else "50_percent" if delay >= 120 else "25_percent" if delay >= 60 else "no_refund"
        categories = [band]
        if start.get("cancelled") is True:
            categories += ["cancellation"]
        if (case.evidence.get("plannedChanges") == 1 and delay is not None
                and case.evidence.get("actual_events") != case.evidence.get("planned_events")):
            # A changed route is not proof of a missed connection: label only the observed property.
            categories += ["changed_one_transfer_route"]
            planned = case.evidence["planned_events"]
            arrive = snapshot.events[planned[1]].get("arrivalEpoch")
            leave = snapshot.events[planned[2]].get("departureEpoch")
            if arrive is not None and leave is not None and arrive + 300 > leave:
                categories += ["missed_connection"]
        for category in categories:
            if category not in selected:
                selected[category] = replace(case, id=f"snapshot_{category}", tags=["snapshot", category])
        if {"no_refund", "25_percent", "50_percent", "handoff", "missed_connection"} <= selected.keys():
            break
    cases = list(selected.values())
    for band, prices in (("25_percent", ("19.60", "20.00", "20.02", "24.00")),
                         ("50_percent", ("9.80", "10.00", "10.01", "12.00"))):
        if band in selected:
            for price in prices:
                original = selected[band]
                derived = _case(snapshot, {**original.request, "price_chf": price}, f"{band}_chf_{price.replace('.', '_')}", hashes)
                cases.append(derived)
    if "25_percent" in selected:
        original = selected["25_percent"]
        cases.append(_case(snapshot, {**original.request, "price_chf": None}, "missing_price", hashes))
        cases.append(_case(snapshot, {**original.request, "day": "2026-11-08"}, "unsupported_day", hashes))
    return {"kind": "snapshot", "version": 1, "created": datetime.now(timezone.utc).isoformat(),
            "snapshot": hashes, "candidate_limit": limit, "examined": examined,
            "coverage": sorted(selected), "unavailable": sorted(
                {"no_refund", "25_percent", "50_percent", "handoff", "missed_connection"} - selected.keys()),
            "verification": "independent oracle only; run the FrameX adapter to cross-check",
            "cases": [case.to_dict() for case in cases]}


def _missed_connection_candidates(snapshot: Snapshot) -> list[tuple[str, str]]:
    candidates = []
    for arrival in snapshot.events.values():
        actual = arrival.get("arrivalEpoch")
        planned = arrival.get("scheduledArrivalEpoch")
        if (actual is None or planned is None or actual - planned < 300
                or arrival.get("cancelled") is not False):
            continue
        first_trip = snapshot.by_trip[arrival["ofTrip"]]
        origins = [k for k in first_trip if snapshot.events[k]["stopSequence"] < arrival["stopSequence"]
                   and snapshot.events[k].get("passThrough") is False
                   and "scheduledDepartureEpoch" in snapshot.events[k]]
        if not origins:
            continue
        for other_key in snapshot.by_station[arrival["atStopPoint"]]:
            other = snapshot.events[other_key]
            depart = other.get("scheduledDepartureEpoch")
            real = other.get("departureEpoch")
            if (depart is None or real is None or other["ofTrip"] == arrival["ofTrip"]
                    or not planned + 300 <= depart <= planned + 3600 or actual + 300 <= real):
                continue
            onward = snapshot.later(other_key, False, "2026-11-07")
            for finish in onward[-2:]:
                candidates.append((origins[-1], snapshot.events[finish]["atStopPoint"]))
    return candidates


def write_discovery(document: dict, output: Path) -> None:
    write_model(SnapshotCases.model_validate(document), output)
