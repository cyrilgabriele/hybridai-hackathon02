"""The independent oracle must search alternatives rather than trust one delayed train."""

import json

from eval.snapshot import Snapshot


def make_snapshot(tmp_path, stops):
    lines = []
    for trip, events in stops.items():
        lines += [f'trip_{trip}[tripRef -> "{trip}"].', f'trip_{trip}[observedOn -> "2026-11-07"].']
        for index, fields in enumerate(events):
            event = {"ofTrip": f"trip_{trip}", "stopSequence": index + 1,
                     "cancelled": False, "passThrough": False, **fields}
            for key, value in event.items():
                rendered = value if key in {"ofTrip", "atStopPoint", "rideSegment"} else json.dumps(value)
                lines.append(f'ev_{trip}_{index}[{key} -> {rendered}].')
    (tmp_path / "70-ist-daten-sbb.fx").write_text("\n".join(lines))
    (tmp_path / "60-spine.fx").write_text('sp_1[designation -> "Origin"].\nsp_2[designation -> "Destination"].')
    return Snapshot(tmp_path)


def test_next_actual_train_and_cancellation_are_independent_of_train_delay(tmp_path):
    snapshot = make_snapshot(tmp_path, {
        "cancelled": [{"atStopPoint": "sp_1", "scheduledDepartureEpoch": 0, "cancelled": True},
                      {"atStopPoint": "sp_2", "scheduledArrivalEpoch": 1000, "cancelled": True}],
        "next": [{"atStopPoint": "sp_1", "scheduledDepartureEpoch": 2000, "departureEpoch": 2000, "rideSegment": "seg_a"},
                 {"atStopPoint": "sp_2", "scheduledArrivalEpoch": 4600, "arrivalEpoch": 4600, "rideSegment": "seg_a"}]})
    result = snapshot.evaluate({"origin": "sp_1", "destination": "sp_2", "board_event": "ev_cancelled_0", "day": "2026-11-07"})
    assert result["delayMinutes"] == 60
    assert result["actual_events"] == ["ev_next_0", "ev_next_1"]


def test_one_change_can_beat_direct_and_missing_real_time_is_not_denial(tmp_path):
    snapshot = make_snapshot(tmp_path, {
        "direct": [{"atStopPoint": "sp_1", "scheduledDepartureEpoch": 0, "departureEpoch": 0, "rideSegment": "s1"},
                   {"atStopPoint": "sp_2", "scheduledArrivalEpoch": 1000, "arrivalEpoch": 5000, "rideSegment": "s1"}],
        "first": [{"atStopPoint": "sp_1", "scheduledDepartureEpoch": 10, "departureEpoch": 10, "rideSegment": "s2"},
                  {"atStopPoint": "sp_3", "scheduledArrivalEpoch": 100, "arrivalEpoch": 100, "rideSegment": "s2"}],
        "second": [{"atStopPoint": "sp_3", "scheduledDepartureEpoch": 500, "departureEpoch": 500, "rideSegment": "s3"},
                   {"atStopPoint": "sp_2", "scheduledArrivalEpoch": 1500, "arrivalEpoch": 1500, "rideSegment": "s3"}]})
    request = {"origin": "sp_1", "destination": "sp_2", "board_event": "ev_direct_0", "day": "2026-11-07"}
    result = snapshot.evaluate(request)
    assert result["actualArrival"] == 1500
    assert result["actualChanges"] == 1
    assert result["delayMinutes"] == 8
    del snapshot.events["ev_direct_1"]["arrivalEpoch"]
    assert snapshot.evaluate(request)["delayMinutes"] is None
    assert snapshot.evaluate({**request, "day": "2026-11-08"})["delayMinutes"] is None


def test_phantom_train_cannot_arrive_before_it_departs(tmp_path):
    snapshot = make_snapshot(tmp_path, {
        "phantom": [{"atStopPoint": "sp_1", "scheduledDepartureEpoch": 2000,
                     "departureEpoch": 2000, "rideSegment": "s1"},
                    {"atStopPoint": "sp_2", "scheduledArrivalEpoch": 1000,
                     "arrivalEpoch": 1000, "rideSegment": "s1"}]})
    assert snapshot.routes("ev_phantom_0", "sp_2", "2026-11-07", actual=False) == []
    assert snapshot.routes("ev_phantom_0", "sp_2", "2026-11-07", actual=True) == []
