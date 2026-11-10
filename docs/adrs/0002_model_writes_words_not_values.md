# 2. The model writes words, the rules write values

Date: 2026-11-10

## Status

Accepted

## Context

Every station, time, date, train, delay and percentage in an answer must come from the knowledge base. [refund-chat.md](../refund-chat.md) fixes the reply as `{"decision", "reply"}` and forbids numbers outside the rule bindings. A check after the writing only catches what it looks for.

## Decision

The phrasing model receives the decision and the names and meanings of the values, never the values. It writes in the passenger's language with placeholders such as `{delay_minutes}`, and the host inserts the values (pattern 12). A reply with a digit, a station name, a wrong decision, an unknown or missing placeholder, or extra sentences is refused and repaired once (pattern 6); then a fixed sentence is used.

Control flow stays in Python as a closed state machine. The rules decide refund, no refund or hand-on. Slots are repaired once, as the language contract says; a cross-check that a quote contains the stated day or hour is added to it.

## Alternatives considered

- Give the model the values and check its text afterwards: more fluent, but correct only by check.
- Fixed templates only: safe, but no passenger language beyond those written by hand.
- FrameX `translator.fx` for slots: its closed value lists do not fit about 1,700 station names.

## Consequences

An invented number cannot reach the passenger. Wording stays the model's, so a plausible but wrong sentence remains possible; the verdict line and the checked times below it are written by the host. Each reply costs one model call of about 3 s.
