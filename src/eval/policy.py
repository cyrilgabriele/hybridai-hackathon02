"""Auditor oracle from Sheet 2, independent of production FrameX rules."""

from decimal import ROUND_HALF_UP, Decimal


def expected_refund(delay_minutes: int | None, price: str | None = None) -> dict:
    if delay_minutes is None:
        return {"decision": "handoff", "refundStatus": None, "refundPercent": None,
                "refundCHF": None, "paidOut": None}
    if isinstance(delay_minutes, bool) or not isinstance(delay_minutes, int) or delay_minutes < 0:
        raise ValueError("delay must be a nonnegative whole number of minutes")
    percent = 0 if delay_minutes < 60 else 25 if delay_minutes < 120 else 50
    result = {"decision": "refund" if percent else "no_refund",
              "delayMinutes": delay_minutes,
              "refundStatus": "entitled" if percent else "notEntitled",
              "refundPercent": percent, "refundCHF": None, "paidOut": None}
    if price is not None:
        amount = Decimal(price)
        if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal("0.01")):
            raise ValueError("price must be finite, nonnegative CHF with at most two decimal places")
        if percent:
            exact = amount * percent / 100
            result["refundCHF"] = str(exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            result["paidOut"] = exact >= Decimal(5)
            if not result["paidOut"]:
                # Passenger-facing action is no payout; status stays entitled.
                result["decision"] = "no_refund"
    return result
