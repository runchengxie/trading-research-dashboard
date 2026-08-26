# Portfolio backtester adapter

`portfolio_adapter.py` is the explicit boundary from a single-symbol Niu Men
signal frame to the sibling `portfolio-backtester` input contract.

It emits three tables:

- `positions`: one long target per Niu Men entry signal
- `periods`: the next-session entry and next-session exit dates, with final
  end-of-data liquidation
- `pricing`: close prices plus explicit entry and exit price columns and any
  available `tradable`, `up_limit`, and `down_limit` columns

Example:

```python
from portfolio_backtester import PositionBacktestConfig, run_position_backtest

from niu_men_line_strategy.portfolio_adapter import build_portfolio_replay_inputs

inputs = build_portfolio_replay_inputs(signals, "600000.SH", weight=0.15)
result = run_position_backtest(
    positions=inputs.positions,
    pricing=inputs.pricing,
    periods=inputs.periods,
    config=PositionBacktestConfig(
        price_col="close",
        entry_price_col="entry_price",
        exit_price_col="exit_price",
    ),
)
```

This is a portfolio replay integration boundary, not a replacement for the
Niu Men event-driven engine. ATR-based position sizing, protective stops,
price-limit blocking, and retry state remain in `run_backtest`. The adapter
does not infer those rules from a target-position schedule. The optional
integration test runs when `portfolio-backtester` is installed; the core Niu
Men package does not acquire a cross-repository runtime dependency.
