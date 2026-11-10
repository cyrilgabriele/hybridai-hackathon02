# Refund chat: language contract

[Project overview](../README.md) · [Ontology](ontology.md)

Domain Expert spec for the fact-safe refund assistant (Hackathon 2). It fixes
what the passenger's words mean, what the model may return, how the rules
critique it, and what each answer must say. The rules decide; the model reads
and phrases.

## Patterns

| Pattern | Where |
|---|---|
| P3 Translator | text in -> slot JSON -> `RefundCase`/`DelayCheck`; verdict and proof -> reply in the passenger's language |
| P1 Sensor | every slot carries the passenger's own words (`quote`); the host accepts it only if the quote occurs in the message |
| P6 Critique & Repair | the rules critique the slots with fixed reasons (below); one repair round, then ask the passenger |
| P4 Model Proposes, Rules Dispose | the model proposes the claim (journey, train); `47-refund-policy.fx` accepts or rejects it |
| P12 Model Selects, Rules Write | the model picks from rule-supplied candidates; every station, time, delay, % and CHF in the reply comes from rule bindings |
| P7 Division by Competence | `handOff` and unresolved slots go to SBB customer service with the reason |

## Slots (model output, P1 + P3)

```json
{
  "origin":      {"station": "St. Gallen", "quote": "St. Gallen"},
  "destination": {"station": "Zürich HB",  "quote": "Zürich HB"},
  "date":        {"value": "2026-11-07",   "quote": "7 November"},
  "time":        {"value": "08:00",        "quote": "8 o'clock"},
  "price":       {"chf": 19.60,            "quote": "19.60"},
  "train":       null
}
```

- `station` is the official designation; the model maps typos, accents and
  languages ("Zurich HB", "Genf"). Any slot not in the message is `null`; the
  model never fills one in.
- The prompt contains the format, this mapping instruction and the meaning of
  each field. It does **not** contain thresholds, percentages, station lists or
  delay arithmetic (Prose Policy).
- Aliases, if added, are FrameX facts, never a Python dictionary (Silent Rule
  Override).

## Critique reasons (P6)

The host and rules check the slot JSON and return these reasons to the model
together with the original message. One repair round, then ask the passenger;
P7 when it cannot be settled.

| Reason | Check | After repair still failing |
|---|---|---|
| `quote_not_found` | quote is not a substring of the message (case-insensitive) | drop slot, ask passenger |
| `unknown_station` | no `?S[designation -> "<station>"]` | ask; if not Swiss, refuse |
| `ambiguous_station` | city name with several stations ("Zürich": 31) | ask with rule-listed candidates |
| `missing_slot` | origin, destination, date or time is `null` | ask for that slot only |
| `date_not_checkable` | `notCheckable` on the case (day not in the data) | P7: only 7 Nov 2026 can be checked |
| `no_departure_in_window` | no `offered(?E)` within ±30 min of the time | ask for the time again |
| `several_departures` | more than one `offered(?E)` | ask the passenger to pick, listing the rule-supplied times and trains |

## Policy (rules: `47-refund-policy.fx`)

| Delay at destination | `refundStatus` | `refundPercent` | The reply names |
|---|---|---|---|
| under 60 min | `notEntitled` | 0 | the delay and the 60 min threshold |
| 60 to 119 min | `entitled` | 25 | the delay and 25 % |
| 120 min or more | `entitled` | 50 | the delay and 50 % |
| amount under CHF 5 (`paidOut -> false`) | `entitled` | 25/50 | that CHF 5 is the minimum payout |
| not measured / day not in data (`handOff`) | none | none | the `handOff` reason; customer service takes over |

Missed connections and cancellations count until the next train that really
arrives (`46-refunds.fx`). Without a price the reply gives the percentage and
the CHF 5 minimum; it asks for the price once.

## Wording

The phrasing model receives the rule bindings and returns
`{"decision": "refund" | "no_refund" | "handoff" | "question", "reply": "..."}`.
The Auditor checks `decision` exactly; `mustSay` substring checks are for
rule-supplied values (station names, minutes, percent), never for "no".

| Outcome | Must say | Must never say |
|---|---|---|
| refund | "Your train from St. Gallen arrived at Zürich HB 72 minutes late. You get 25 % of the ticket price back (CHF 4.90)." | a number not in the bindings |
| below CHF 5 | "...25 % would be CHF 4.90, below the CHF 5 minimum payout, so nothing is paid out." | "you get CHF 4.90" |
| no refund | "...arrived 45 minutes late. Refunds start at 60 minutes of delay." | "your train was on time" unless delay is 0 |
| handoff | "I can't check this: <handOff reason>. SBB customer service will look at it." | yes, no, or a guessed delay |
| interpretation | "I read 'Zurich' as Zürich HB." | a silent correction |
| technical error | "Something went wrong. Please try again." | any verdict |

Reply in the passenger's language; station names stay official.
