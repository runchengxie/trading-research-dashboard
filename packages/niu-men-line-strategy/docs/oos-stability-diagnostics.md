# OOS Stability Diagnostics

This extension keeps the existing full-market rolling OOS baseline unchanged and adds diagnostics for local parameter sensitivity, coverage loss, and execution constraints.

## Reset neighborhood

The baseline remains `reset_bars=5`. Optional sensitivity variants can be added with:

```bash
uv run python scripts/run_industry_context_oos.py \
  ... \
  --reset-bars-neighborhood 3,4,5,6,7
```

The runner normalizes positive unique values. The baseline value 5 is not duplicated. Other values are emitted as `nml_reset_<bars>` variants and flow through the existing folds, summaries, and paired baseline comparisons.

When the option is omitted, the existing strategy variant set is unchanged.

## Eligibility-stage diagnostics

Where available, skip rows and evaluated fold rows now include:

- `raw_bars`: adjusted daily bars loaded for the symbol.
- `mapped_industry_bars`: bars with a point-in-time mapped industry.
- `pit_eligible_bars`: mapped bars eligible under the lagged point-in-time universe rule.
- `context_ready_bars`: eligible bars with ready ETF industry context.

The additional explicit skip reasons `no_raw_bars`, `no_mapped_industry_bars`, and `no_pit_eligible_bars` distinguish coverage loss before the existing `insufficient_context_ready_bars` condition.

## Limit-lock attribution

Strategy fold metrics retain:

- `blocked_entry_count`
- `blocked_exit_day_count`

They additionally report:

- `blocked_smx_exit_day_count`
- `blocked_stop_exit_day_count`

`blocked_exit_day_count` counts unique days on which an open-position sell could not execute at the down-limit open. The two reason-specific counts describe which pending exit conditions were blocked. A single day can have both an SMX exit and a protective stop pending, so reason-specific counts may overlap and do not have to sum to the unique-day total.

The OOS manifest aggregates all four counts by variant.

## Market-stage decomposition

This change deliberately does not label calendar ranges as bull, bear, or sideways markets. The repository does not yet define a versioned point-in-time market-regime contract for full-market OOS use. Such a decomposition should first define that regime using information available at each test bar and then join it by date. Hard-coded historical period labels would introduce an untracked research assumption and are therefore deferred.
