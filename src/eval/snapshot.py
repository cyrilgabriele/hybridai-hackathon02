"""Read snapshot facts and enumerate journeys without executing production rules."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROPERTY = re.compile(r'(\w+)\[(\w+) -> (.*)\]\.\s*$')
MAX_START_WAIT = 10800
MAX_CHANGE_WAIT = 3600
MAX_JOURNEY = 14400
MISSING_PLAN = "the planned train's arrival at the destination has no recorded actual time"
MISSING_ACTUAL = "no actual arrival at the destination is recorded within three hours of the planned departure"
WRONG_DAY = "journeys on this day are not in the SBB data"


@dataclass(frozen=True)
class Route:
    arrival: int
    events: tuple[str, ...]
    changes: int


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(workspace: Path) -> dict[str, str]:
    files = [*sorted(workspace.glob("*.fx")), workspace / "manifest.json"]
    return {p.name: file_hash(p) for p in files if p.is_file()}


class Snapshot:
    """Scalar source facts plus indexes; deliberately independent of FrameX queries."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.events: dict[str, dict[str, Any]] = {}
        self.trips: dict[str, dict[str, Any]] = {}
        self.names: dict[str, str] = {}
        self.by_trip: dict[str, list[str]] = defaultdict(list)
        self.by_station: dict[str, list[str]] = defaultdict(list)
        self._feed_cache: dict[tuple, dict[str, list[tuple[str, str]]]] = {}
        self._read(workspace / "60-spine.fx", self.names)
        self._read(workspace / "70-ist-daten-sbb.fx", self.names)
        for key, event in self.events.items():
            self.by_trip[event["ofTrip"]].append(key)
            self.by_station[event["atStopPoint"]].append(key)
        for keys in self.by_trip.values():
            keys.sort(key=lambda key: self.events[key]["stopSequence"])
        self.days = {v["observedOn"] for v in self.trips.values() if "observedOn" in v}

    def _read(self, path: Path, names: dict[str, str]) -> None:
        with path.open() as source:
            for line in source:
                match = PROPERTY.fullmatch(line)
                if not match:
                    continue
                obj, slot, raw = match.groups()
                if not obj.startswith(("ev_", "trip_")) and slot != "designation":
                    continue
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    value = raw
                if slot == "designation":
                    names[obj] = value
                elif obj.startswith("ev_"):
                    self.events.setdefault(obj, {})[slot] = value
                elif obj.startswith("trip_"):
                    self.trips.setdefault(obj, {})[slot] = value

    def _eligible(self, key: str, actual: bool, day: str) -> bool:
        event = self.events[key]
        return (event.get("passThrough") is False
                and self.trips[event["ofTrip"]].get("observedOn") == day
                and (not actual or (event.get("cancelled") is False and "rideSegment" in event)))

    def later(self, board: str, actual: bool, day: str) -> list[str]:
        event = self.events[board]
        return [key for key in self.by_trip[event["ofTrip"]]
                if self.events[key]["stopSequence"] > event["stopSequence"]
                and self._eligible(key, actual, day)
                and (not actual or self.events[key].get("rideSegment") == event.get("rideSegment"))]

    def feeds(self, destination: str, actual: bool, day: str) -> dict[str, list[tuple[str, str]]]:
        cache_key = (destination, actual, day)
        if cache_key in self._feed_cache:
            return self._feed_cache[cache_key]
        result: dict[str, list[tuple[str, str]]] = defaultdict(list)
        arrival_slot = "arrivalEpoch" if actual else "scheduledArrivalEpoch"
        for alight in self.by_station[destination]:
            finish = self.events[alight]
            if not self._eligible(alight, actual, day) or arrival_slot not in finish:
                continue
            for board in self.by_trip[finish["ofTrip"]]:
                start = self.events[board]
                if start["stopSequence"] >= finish["stopSequence"]:
                    break
                if (self._eligible(board, actual, day)
                        and (not actual or start.get("rideSegment") == finish.get("rideSegment"))):
                    result[start["atStopPoint"]].append((board, alight))
        self._feed_cache[cache_key] = result
        return result

    def routes(self, board: str, destination: str, day: str, *, actual: bool,
               transfer: int = 300, latest: int | None = None) -> list[Route]:
        if not self._eligible(board, actual, day):
            return []
        start = self.events[board]
        departure_slot = "departureEpoch" if actual else "scheduledDepartureEpoch"
        arrival_slot = "arrivalEpoch" if actual else "scheduledArrivalEpoch"
        if departure_slot not in start:
            return []
        result = []
        feeds = self.feeds(destination, actual, day)
        for first_end in self.later(board, actual, day):
            middle = self.events[first_end]
            arrival = middle.get(arrival_slot)
            if arrival is None or arrival <= start[departure_slot]:
                continue
            station = middle["atStopPoint"]
            if station == destination:
                if latest is None or arrival <= latest:
                    result.append(Route(arrival, (board, first_end), 0))
                continue
            if station == start["atStopPoint"]:
                continue
            for second_board, finish in feeds.get(station, []):
                other = self.events[second_board]
                dep = other.get(departure_slot)
                end = self.events[finish][arrival_slot]
                if (other["ofTrip"] != start["ofTrip"] and dep is not None
                        and arrival + transfer <= dep <= arrival + MAX_CHANGE_WAIT
                        and end > dep and (latest is None or end <= latest)):
                    result.append(Route(end, (board, first_end, second_board, finish), 1))
        return sorted(result, key=lambda route: (route.arrival, route.changes, route.events))

    def evaluate(self, request: dict) -> dict:
        """Compute a pinned boarding event's plan and earliest actual alternative."""
        day, board = request["day"], request["board_event"]
        if day not in self.days:
            return {"delayMinutes": None, "reasons": [WRONG_DAY], "offered": False}
        start = self.events[board]
        if start["atStopPoint"] != request["origin"]:
            raise ValueError("boarding event does not belong to the requested origin")
        departure = start["scheduledDepartureEpoch"]
        transfer = request.get("transfer_seconds", 300)
        destination = request["destination"]
        plans = self.routes(board, destination, day, actual=False, transfer=transfer)
        if not plans:
            return {"delayMinutes": None, "reasons": ["no planned journey"], "offered": False}
        best = plans[0]
        winning_plans = [p for p in plans if p.arrival == best.arrival]
        on_record = start.get("cancelled") is True or any(
            "arrivalEpoch" in self.events[p.events[-1]]
            or self.events[p.events[-1]].get("cancelled") is True for p in winning_plans)
        alternatives = []
        for key in self.by_station[request["origin"]]:
            event = self.events[key]
            dep = event.get("departureEpoch")
            if dep is not None and departure <= dep <= departure + MAX_START_WAIT:
                alternatives.extend(self.routes(key, destination, day, actual=True,
                                                transfer=transfer,
                                                latest=departure + MAX_START_WAIT + MAX_JOURNEY))
        actual = min(alternatives, key=lambda route: (route.arrival, route.changes, route.events), default=None)
        reasons = ([] if on_record else [MISSING_PLAN]) + ([] if actual else [MISSING_ACTUAL])
        offered = self._offered(request, departure, best.arrival)
        return {"delayMinutes": max(0, (actual.arrival - best.arrival) // 60) if actual and on_record else None,
                "plannedArrival": best.arrival, "actualArrival": actual.arrival if actual else None,
                "plannedChanges": best.changes, "actualChanges": actual.changes if actual else None,
                "planned_events": list(best.events), "actual_events": list(actual.events) if actual else [],
                "reasons": reasons, "offered": offered}

    def _offered(self, request: dict, departure: int, arrival: int) -> bool:
        center = request.get("window_center", departure)
        if not center - 1800 <= departure <= center + 1800:
            return False
        for key in self.by_station[request["origin"]]:
            dep = self.events[key].get("scheduledDepartureEpoch")
            if dep is None or not departure <= dep <= center + 1800:
                continue
            routes = self.routes(key, request["destination"], request["day"], actual=False,
                                 transfer=request.get("transfer_seconds", 300))
            if routes and routes[0].arrival < arrival:
                return False
        return True
