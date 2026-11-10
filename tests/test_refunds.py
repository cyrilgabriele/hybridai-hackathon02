"""Refund delay rules (46-refunds.fx): planned against actual arrival at the destination."""
from __future__ import annotations

import json

import pytest

from ontology import service
from tests.test_regression import DAY, client, load, stop  # noqa: F401  (client is a fixture)

ORIGIN, DESTINATION, VIA = 1, 2, 3


def late(trip, station, planned, actual, **extra):
    """A stop planned at one time that really happened at another."""
    row = stop(trip, station, planned, **extra)
    row["an_prognose"] = row["ab_prognose"] = f"{DAY}T{actual}:00"
    return row


def epoch(clock):
    return service.timestamp(f"{DAY}T{clock}:00")


def case(client, rows, around="08:00", window=30):
    from ontology.ids import Scope
    load(client, rows, Scope({ORIGIN, DESTINATION, VIA}))
    stated = epoch(around)
    client.add(source=f'x:RefundCase[origin -> sp_{ORIGIN}; destination -> sp_{DESTINATION}; '
                      f'onDay -> "{DAY}"; windowFrom -> {stated - window * 60}; '
                      f'windowTo -> {stated + window * 60}; transferSeconds -> 300].')


def departures(client):
    found = client.query("?- x[plannedArrival(?E) -> ?A; plannedChanges(?E) -> ?C] "
                         "AND ?E[scheduledDepartureEpoch -> ?D].")
    return sorted((int(r["D"]), int(r["A"]), int(r["C"])) for r in found.get("bindings", []))


def check(client, departure):
    found = client.query(f"?- x[plannedArrival(?E) -> ?A] AND ?E[scheduledDepartureEpoch -> {epoch(departure)}].")
    board = found["bindings"][0]["E"]
    client.add(source=f"y:DelayCheck[checkOf -> x; plannedBoard -> {board}].")


def value(client, slot):
    found = client.query(f"?- y[{slot} -> ?V].").get("bindings", [])
    return [json.loads(r["V"]) for r in found]


def test_a_late_direct_train_is_its_delay(client):
    case(client, [stop("ic", ORIGIN, "08:00"), late("ic", DESTINATION, "09:00", "10:05")])
    assert departures(client) == [(epoch("08:00"), epoch("09:00"), 0)]
    check(client, "08:00")
    assert value(client, "delayMinutes") == [65]
    assert value(client, "delayMeasured") == [True]


def test_a_missed_connection_counts_until_the_next_train_arrives(client):
    # Planned: change at VIA with 10 minutes. The first train is 15 minutes late,
    # so the passenger takes the next train an hour later.
    rows = [stop("a", ORIGIN, "08:00"), late("a", VIA, "08:30", "08:45"),
            stop("b", VIA, "08:40"), stop("b", DESTINATION, "09:10"),
            stop("c", VIA, "09:40"), stop("c", DESTINATION, "10:10")]
    case(client, rows)
    check(client, "08:00")
    assert value(client, "plannedArrival") == [epoch("09:10")]
    assert value(client, "actualArrival") == [epoch("10:10")]
    assert value(client, "delayMinutes") == [60]


def test_a_cancelled_train_is_replaced_by_the_next_one(client):
    rows = [dict(stop("ic", ORIGIN, "08:00"), faellt_aus_tf=True),
            dict(stop("ic", DESTINATION, "09:00"), faellt_aus_tf=True),
            stop("next", ORIGIN, "10:00"), stop("next", DESTINATION, "11:00")]
    case(client, rows)
    # The cancelled train was planned, so the passenger can name it.
    assert departures(client)[0][:2] == (epoch("08:00"), epoch("09:00"))
    check(client, "08:00")
    assert value(client, "planCancelled") == [True]
    assert value(client, "delayMinutes") == [120]
    assert value(client, "delayMeasured") == [True]


def test_arriving_on_time_is_no_delay(client):
    case(client, [stop("ic", ORIGIN, "08:00"), late("ic", DESTINATION, "09:00", "08:58")])
    check(client, "08:00")
    assert value(client, "delayMinutes") == [0]


def test_a_missing_actual_time_at_the_destination_is_not_measured(client):
    rows = [stop("ic", ORIGIN, "08:00"),
            dict(stop("ic", DESTINATION, "09:00"), an_prognose_status="PROGNOSE"),
            stop("next", ORIGIN, "09:00"), stop("next", DESTINATION, "10:00")]
    case(client, rows)
    check(client, "08:00")
    # The next train would suggest an hour's delay, but the plan's own arrival
    # is not on record: the rules refuse to guess upwards.
    assert value(client, "delayMeasured") == []
    assert value(client, "notMeasured") == ["the planned train's arrival at the destination has no recorded actual time"]


def test_departures_outside_the_window_are_not_offered(client):
    case(client, [stop("early", ORIGIN, "07:00"), stop("early", DESTINATION, "08:00"),
                  stop("ic", ORIGIN, "08:10"), stop("ic", DESTINATION, "09:10")])
    assert [d for d, _, _ in departures(client)] == [epoch("08:10")]


def test_a_departure_beaten_by_a_later_one_is_not_offered(client):
    # The 08:05 detour arrives after the 08:10 direct train: nobody plans it.
    case(client, [stop("slow", ORIGIN, "08:05"), stop("slow", VIA, "08:30"),
                  stop("back", VIA, "08:40"), stop("back", DESTINATION, "09:40"),
                  stop("ic", ORIGIN, "08:10"), stop("ic", DESTINATION, "09:10")])
    offered = client.query("?- x[offered(?E) -> ?A] AND ?E[scheduledDepartureEpoch -> ?D].")["bindings"]
    assert [int(r["D"]) for r in offered] == [epoch("08:10")]


# --------------------------------------------------------------------
# Refund policy (47-refund-policy.fx): Sheet 2 thresholds and payout
# --------------------------------------------------------------------

def delayed_by(client, minutes, price=None):
    """One direct train planned 08:00 to 09:00, arriving `minutes` late."""
    arrival = 9 * 60 + minutes  # Swiss clock minutes after midnight
    actual = f"{arrival // 60:02d}:{arrival % 60:02d}"
    case(client, [stop("ic", ORIGIN, "08:00"), late("ic", DESTINATION, "09:00", actual)])
    check(client, "08:00")
    if price is not None:
        client.add(source=f"y[ticketPriceRappen -> {price}].")


@pytest.mark.parametrize("minutes, percent, status", [
    (0, 0, "notEntitled"), (59, 0, "notEntitled"),
    (60, 25, "entitled"), (119, 25, "entitled"),
    (120, 50, "entitled"), (130, 50, "entitled"),
])
def test_the_delay_band_decides_the_refund_share(client, minutes, percent, status):
    delayed_by(client, minutes)
    assert value(client, "delayMinutes") == [minutes]
    assert value(client, "refundPercent") == [percent]
    assert value(client, "refundStatus") == [status]
    assert value(client, "handOff") == []


def test_without_a_price_there_is_no_amount(client):
    delayed_by(client, 70)
    assert value(client, "refundPercent") == [25]
    assert value(client, "refundRappen") == []
    assert value(client, "paidOut") == []


def test_a_refund_under_five_francs_is_entitled_but_not_paid_out(client):
    delayed_by(client, 70, price=1960)  # 25 % of CHF 19.60 = CHF 4.90
    assert value(client, "refundRappen") == [490]
    assert value(client, "refundStatus") == ["entitled"]
    assert value(client, "paidOut") == [False]


def test_a_refund_of_five_francs_or_more_is_paid_out(client):
    delayed_by(client, 130, price=4400)  # 50 % of CHF 44.00
    assert value(client, "refundRappen") == [2200]
    assert value(client, "paidOut") == [True]


def test_no_refund_has_no_amount_even_with_a_price(client):
    delayed_by(client, 45, price=4400)
    assert value(client, "refundStatus") == ["notEntitled"]
    assert value(client, "refundRappen") == []


def test_an_unmeasured_delay_gets_no_verdict_and_goes_to_customer_service(client):
    rows = [stop("ic", ORIGIN, "08:00"),
            dict(stop("ic", DESTINATION, "09:00"), an_prognose_status="PROGNOSE"),
            stop("next", ORIGIN, "10:00"), stop("next", DESTINATION, "11:00")]
    case(client, rows)
    check(client, "08:00")
    # The next train suggests 120 minutes, but the plan is not on record.
    assert value(client, "refundStatus") == []
    assert value(client, "refundPercent") == []
    assert value(client, "handOff") == ["the planned train's arrival at the destination has no recorded actual time"]


def test_a_day_outside_the_data_cannot_be_checked(client):
    case(client, [stop("ic", ORIGIN, "08:00"), stop("ic", DESTINATION, "09:00")])
    client.add(source=f'z:RefundCase[origin -> sp_{ORIGIN}; destination -> sp_{DESTINATION}; '
                      f'onDay -> "2026-11-08"; windowFrom -> 0; windowTo -> 1; transferSeconds -> 300].')
    assert client.query('?- z[notCheckable -> ?V].').get("bindings")
    assert not client.query('?- x[notCheckable -> ?V].').get("bindings")
