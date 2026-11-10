// ====================================================================
// Refund policy (Hackathon 2, Flight mode Sheet 2)
//
// Simplified SBB passenger rights, applied to the delay at the destination
// that 46-refunds.fx measures for a DelayCheck:
//
//   under 60 min      no refund, the answer names the threshold   notEntitled
//   60 min or more    25 % of the ticket price                    entitled
//   120 min or more   50 % of the ticket price                    entitled
//   refund under CHF 5  not paid out, the answer names the minimum entitled
//   not measurable    no verdict, hand on to customer service
//
// Every number lives in refundPolicy, so `explain` shows the threshold
// behind each verdict and the chat never states one from memory.
// Money is in Rappen (integers), so CHF 12.40 is 1240.
// ====================================================================

refundPolicy[thresholdMinutes -> 60; higherThresholdMinutes -> 120;
             lowerPercent -> 25; higherPercent -> 50; minimumPayoutRappen -> 500].

// The price the passenger paid, stated by the passenger (host-checked quote).
DelayCheck { ticketPriceRappen: Integer }.

// --------------------------------------------------------------------
// The day: only operating days present in the data can be checked
// --------------------------------------------------------------------
closed slot dayOnRecord.
?X[dayOnRecord -> true] <- ?X:RefundCase[onDay -> ?D] AND ?T:Trip[observedOn -> ?D].
?X[notCheckable -> "journeys on this day are not in the SBB data"]
    <- ?X:RefundCase AND NOT ?X[dayOnRecord -> true].

// --------------------------------------------------------------------
// Refund share, only for a measured delay
// --------------------------------------------------------------------
?Y[refundPercent -> 0] <- ?Y[delayMeasured -> true; delayMinutes -> ?M]
    AND refundPolicy[thresholdMinutes -> ?T] AND ?M < ?T.
?Y[refundPercent -> ?P] <- ?Y[delayMeasured -> true; delayMinutes -> ?M]
    AND refundPolicy[thresholdMinutes -> ?T; higherThresholdMinutes -> ?H; lowerPercent -> ?P]
    AND ?M >= ?T AND ?M < ?H.
?Y[refundPercent -> ?P] <- ?Y[delayMeasured -> true; delayMinutes -> ?M]
    AND refundPolicy[higherThresholdMinutes -> ?H; higherPercent -> ?P] AND ?M >= ?H.

?Y[refundStatus -> "notEntitled"] <- ?Y[refundPercent -> 0].
?Y[refundStatus -> "entitled"] <- ?Y[refundPercent -> ?P] AND ?P > 0.

// --------------------------------------------------------------------
// Amount and payout, only when the passenger named the price
// --------------------------------------------------------------------
?Y[refundRappen -> ?R] <- ?Y[refundPercent -> ?P; ticketPriceRappen -> ?C] AND ?P > 0
    AND ?X := ?C * ?P AND ?Q := ?X / 100 AND ?R := floor(?Q).
?Y[paidOut -> true] <- ?Y[refundRappen -> ?R]
    AND refundPolicy[minimumPayoutRappen -> ?Min] AND ?R >= ?Min.
?Y[paidOut -> false] <- ?Y[refundRappen -> ?R]
    AND refundPolicy[minimumPayoutRappen -> ?Min] AND ?R < ?Min.

// --------------------------------------------------------------------
// No verdict: customer service takes over, with the reason
// --------------------------------------------------------------------
?Y[handOff -> ?Why] <- ?Y:DelayCheck[notMeasured -> ?Why].
?Y[handOff -> ?Why] <- ?Y:DelayCheck[checkOf -> ?X] AND ?X[notCheckable -> ?Why].
