# Contextual Setup Point-in-Time Review

## Why this review exists

The first contextual-research implementation had two research-validity problems that ordinary unit tests did not expose immediately:

1. the Dashboard's static `yesterdayHigh` / `yesterdayLow` fields describe the latest completed trading day at snapshot-generation time, while the committed `intraday` series also describes that same day;
2. final-day VWAP and ORB values are only fully known after part or all of the session has elapsed.

Using those values indiscriminately to detect earlier events would create look-ahead bias: the detector would appear to know the day's completed high/low, final VWAP, or final ORB before those values existed.

A separate review also found that intermarket peer selection used absolute correlation while extreme confirmation originally assumed positive correlation. That would misclassify inverse relationships such as a dollar index versus equity index.

## Corrected point-in-time rules

### Prior-day / prior-5-day levels

For an intraday research date `D`, the detector now derives:

- `previous_day_high`
- `previous_day_low`
- `previous_5d_high`
- `previous_5d_low`

only from daily rows whose date is strictly `< D`.

The static snapshot's `indicators.yesterdayHigh` and `indicators.yesterdayLow` are not used as historical setup levels.

### VWAP

The existing Dashboard snapshot exposes a completed-day VWAP. It is retained as an ex-post context/reference value and is labelled `VWAP（日终上下文）`.

`setup-detector.v1` does not use this VWAP as a historical trigger. A future live/point-in-time VWAP feature would need a separately derived rolling series.

### ORB

ORB values are allowed in setup detection only after the configured opening-range window has completed:

- US: 10:30 local time
- CN: 10:00 local time
- HK: 10:00 local time

The detector ignores ORB levels for earlier timestamps.

### Higher-timeframe context

`higherTimeframe` uses only the 20 daily rows preceding the intraday research date. The current day's daily bar does not participate.

### Outcome labels

Forward returns and MFE/MAE intentionally use future bars after an event. They are outcome labels, not trigger inputs. Keeping this distinction explicit is required for later conditional-expectancy research.

## Ex-post descriptors

The following current v1 fields are completed-day research descriptors and must not be silently reinterpreted as live entry features:

- `dayArchetype`
- final session summaries
- completed-day VWAP
- current daily-bar intermarket extreme confirmation

They are legitimate for historical grouping, diagnostics and outcome analysis. A live strategy filter needs a point-in-time version with its own semantics and tests.

## Intermarket correlation direction

Peer selection continues to rank by absolute 20-return correlation, but confirmation now respects the sign:

- positive correlation: high ↔ high, low ↔ low;
- negative correlation: high ↔ low, low ↔ high.

A dedicated inverse-correlation regression test covers this behavior.

## Regression coverage added

Tests now explicitly verify that:

- a current-day daily high cannot become that same day's `previous_day_high`;
- HTF context excludes the current research day;
- VWAP never appears in `setup-detector.v1` events;
- ORB levels cannot generate setup events before the ORB availability time;
- inverse-correlated peers confirm opposite extremes instead of being treated as divergent by construction.

## Research interpretation

The practical distinction is:

```text
point-in-time features -> event trigger
future bars            -> outcome labels
completed-day features -> ex-post grouping / diagnostics
```

Mixing these categories would produce attractive but invalid statistics. The contracts and documentation keep them separate so future history aggregation can remain causally honest.
