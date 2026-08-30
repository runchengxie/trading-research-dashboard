# Contextual Research Completion Design

## Goal

Complete the contextual research layer so it can move from a single-day observational panel to a causally explicit, multi-day conditional research artifact without changing the existing strategy snapshot contract or inventing economic-event data.

## Scope

### Included

- A versioned `trading_research.conditional_research.v1` artifact summarizing multiple contextual snapshots and optional normalized strategy outcomes.
- Conditional groups keyed by observable context: instrument, market, session, day archetype, setup event, reference level, strategy, and variant.
- Sample count, win rate, expectancy, mean return, MFE, MAE, date coverage, and instrument coverage.
- Complete available reference/session semantics: previous-week levels, session open/high/low, volume share, first HOD/LOD timestamps, and opening gap percentage.
- Point-in-time-safe context/trigger metadata on setup events.
- Timezone normalization for event-study input and session classification.
- Canonical nested JSON Schema validation, static publication validation, and frontend validation.
- Dashboard Setup Checklist and conditional-statistics display with explicit empty states.

### Excluded

- A third-party economic-calendar provider. The existing normalized `--events` input remains the boundary.
- ICT-specific scoring, strategy rules, or causal claims.
- Inferring strategy-conditional performance from aggregate strategy metrics.
- Treating ex-post day archetype or completed-day intermarket observations as live entry filters.
- Committing raw market history or large generated artifacts.

## Data flow

```text
data.json.contextualResearch (one date) ─┐
                                          ├─ contextual-history summarizer ─ conditional-research.v1
normalized strategy outcomes (optional) ──┘

data.json.contextualResearch + optional data.json.conditionalResearch
                                      └─ Dashboard Setup Checklist / conditional statistics
```

The current one-day contextual snapshot remains the source of factual context and event outcomes. The history summarizer consumes a sequence of already validated snapshots; it does not fetch data or silently fill missing days.

## Contracts

### `trading_research.conditional_research.v1`

The artifact contains:

- `generatedAt`, `dateRange`, and `sourceSnapshots`;
- `quality` and `coverage`;
- `groups`, each with explicit nullable dimensions and metrics;
- `provenance`.

Each group records `sampleCount`, `winRate`, `expectancy`, `meanReturn`, `meanMfe`, `meanMae`, `dateCount`, and `instrumentCount`. Returns are decimal returns. A missing outcome is excluded from outcome metrics but remains visible in coverage through `sampleCount`.

Normalized strategy outcome inputs have the shape:

```json
{
  "strategyId": "r-breaker",
  "variantId": "default",
  "instrument": "TSLA.US",
  "dataDate": "2026-08-28",
  "session": "opening_range",
  "eventType": "break_and_hold_above",
  "referenceLevelKind": "previous_day_high",
  "return": 0.012,
  "mfe": 0.018,
  "mae": -0.004,
  "rMultiple": 1.2,
  "win": true
}
```

The summarizer uses `return` for expectancy and win rate when `win` is absent. It never derives a conditional strategy result from a strategy snapshot's aggregate metrics.

### Existing contracts

`market_context.v1` and `setup_event.v1` remain version-compatible. New context/trigger fields and complete session/reference fields are optional in the schema so existing snapshots remain readable. The `contextual_snapshot.v1` schema embeds the nested definitions instead of accepting arbitrary objects.

## Research semantics

- Prior-week levels use daily rows strictly before the intraday research date.
- Session summaries use instrument-local time and expose only observations present in the input.
- Session volume is optional when intraday rows have no volume.
- Event timestamps without an offset are interpreted in the instrument timezone; offset-aware timestamps are converted into it before date/window checks.
- Forward returns and MFE/MAE remain outcome labels and never enter setup detection.
- Conditional groups are descriptive statistics over supplied samples, not trading recommendations.

## Publication and UI

The enrichment CLI accepts optional contextual-history inputs and strategy-outcome inputs. Without them, it preserves the current one-day `contextualResearch` behavior. With a validated history artifact, it writes optional `conditionalResearch` into the Dashboard document.

The workspace displays:

- a current-condition checklist for HTF trend, day archetype, session, reference level, and intermarket observation;
- matching historical sample counts and outcome metrics when `conditionalResearch` is present;
- an explicit “no multi-day conditional artifact published” state otherwise.

## Failure handling

- Invalid nested contextual data fails canonical validation before publication.
- Invalid conditional artifacts fail publication before replacing a target.
- Missing history or strategy outcomes are represented as empty/unknown coverage, not fabricated metrics.
- Existing Dashboard rendering continues when optional contextual or conditional data is absent or malformed.

## Acceptance criteria

1. Existing contextual and strategy snapshot consumers remain compatible.
2. A two-date fixture produces deterministic conditional groups and correct aggregate metrics.
3. A malformed nested context is rejected by both Python and standalone JSON Schema validation.
4. An offset-aware event produces the same local-day study as an equivalent local timestamp.
5. The frontend renders checklist and metrics only from supplied conditional data.
6. Existing Python and frontend test suites, lint, build, and static snapshot validation pass.
