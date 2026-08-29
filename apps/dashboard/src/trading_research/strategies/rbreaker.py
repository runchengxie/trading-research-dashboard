"""R-Breaker 日内策略回测模块。

来源: wu-intraday-strategy 项目 (t0.py / t.py)，已迁移整合至此。

数据源:
- akshare: 无需 token，分钟数据经 stock_zh_a_hist_min_em 获取
- tushare: 需要 token，通过环境变量 TUSHARE_TOKEN 或命令行 --tushare-token 提供
  (原 t.py 中硬编码的 token 已移除，请勿将 token 提交到仓库)

用法示例:
    python backtest/rbreaker.py --symbol 603356 --data-source akshare
    python backtest/rbreaker.py --symbol 603356 --data-source tushare --in-sample-start 2025-06-01 --in-sample-end 2025-06-23 --out-sample-start 2025-06-24
"""

import argparse
import math
from datetime import datetime
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from trading_research.strategies import rbreaker_data
from trading_research.strategies.rbreaker_data import (
    get_recent_trading_days_with_prev,
    load_minute_data_akshare,
    load_or_download_data,
)
from trading_research.strategies.rbreaker_strategy import (
    CustomPandasData,
    RBreakerStrategy,
    bt,
    is_session_close_or_later,  # noqa: F401 - retained as a public compatibility export
)

download_stock_data_tushare = rbreaker_data.download_stock_data_tushare

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def annualized_sharpe_from_returns(values) -> float:
    """Return a finite daily Sharpe value for a strategy return series."""
    returns = np.asarray(list(values), dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return 0.0
    volatility = float(returns.std(ddof=1))
    if volatility == 0.0:
        return 0.0
    return float(returns.mean() / volatility * math.sqrt(252))

# ==============================================================================
# 数据下载与加载
# ==============================================================================

# ==============================================================================
# 回测与参数优化
# ==============================================================================

def optimize_strategy(data, prev_day_data):
    """参数优化 - 综合考虑夏普比率和信号准确率 (来自 t.py)。"""
    if bt is None:
        raise RuntimeError("未安装 backtrader，请执行: pip install backtrader")
    assert bt is not None

    cerebro = bt.Cerebro()
    cerebro.adddata(data)

    f1_values = np.arange(0.15, 0.55, 0.05)
    f2_values = np.arange(0.02, 0.18, 0.02)
    f3_values = np.arange(0.05, 0.45, 0.05)
    total_combinations = len(f1_values) * len(f2_values) * len(f3_values)

    cerebro.optstrategy(
        RBreakerStrategy,
        f1=f1_values,
        f2=f2_values,
        f3=f3_values,
        prev_day_high=prev_day_data[0],
        prev_day_low=prev_day_data[1],
        prev_day_close=prev_day_data[2],
    )

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

    print(f"开始参数优化，共 {total_combinations} 个参数组合，请稍候...")
    opt_results = cerebro.run(maxcpus=1)

    best_score = -np.inf
    best_params = None
    best_results = {}

    for run in opt_results:
        for strat in run:
            sharpe = strat.analyzers.sharpe.get_analysis()['sharperatio']
            if sharpe is None:
                sharpe = 0.0

            try:
                signal_count = len(strat.trade_signals)
                evaluated_signals = [s for s in strat.trade_signals if s['evaluated']]
            except AttributeError:
                signal_count = 0
                evaluated_signals = []

            accuracy = 0.0
            if evaluated_signals:
                correct_count = sum(1 for s in evaluated_signals if s['outcome'] == 'Correct')
                accuracy = correct_count / len(evaluated_signals) * 100

            score = sharpe + accuracy * 0.05
            if signal_count < 15:
                score -= 10

            if score > best_score:
                best_score = score
                best_params = strat.p
                best_results = {
                    'score': score, 'sharpe': sharpe,
                    'accuracy': accuracy, 'signal_count': signal_count,
                }

    print(f"参数优化完成！共测试了 {total_combinations} 个参数组合。")
    return best_params, best_results


def run_strategy(data, params, prev_day_data, plot=False, save_trades=False, filename_prefix=""):
    """使用给定参数运行策略，返回详细结果。"""
    if bt is None:
        raise RuntimeError("未安装 backtrader，请执行: pip install backtrader")
    assert bt is not None

    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(
        RBreakerStrategy,
        f1=params.f1, f2=params.f2, f3=params.f3,
        reverse=params.reverse, rangemin=params.rangemin,
        prev_day_high=prev_day_data[0],
        prev_day_low=prev_day_data[1],
        prev_day_close=prev_day_data[2],
        session_close_hour=getattr(params, "session_close_hour", 14),
        session_close_minute=getattr(params, "session_close_minute", 55),
        printlog=True,
    )

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return', timeframe=bt.TimeFrame.Days)

    results = cerebro.run()
    strat = results[0]

    if plot:
        print("正在生成回测图表...")
        cerebro.plot(style='candlestick', iplot=False)

    evaluated_signals = [s for s in strat.trade_signals if s['evaluated']]
    accuracy = 0.0
    if evaluated_signals:
        correct_count = sum(1 for s in evaluated_signals if s['outcome'] == 'Correct')
        accuracy = correct_count / len(evaluated_signals) * 100

    if save_trades and strat.trade_records:
        trades_df = pd.DataFrame(strat.trade_records)
        trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])
        trades_df = trades_df.sort_values('datetime')

        cumulative_pnl = 0.0
        for i, trade in trades_df.iterrows():
            if trade['action'] == 'SELL':
                buy_trades = trades_df[(trades_df['action'] == 'BUY') & (trades_df.index < i)]
                if not buy_trades.empty:
                    last_buy = buy_trades.iloc[-1]
                    pnl = (trade['price'] - last_buy['price']) * trade['size'] - trade['commission'] - last_buy['commission']
                    cumulative_pnl += pnl
                    trades_df.at[i, 'pnl'] = pnl
                    trades_df.at[i, 'cumulative_pnl'] = cumulative_pnl

        csv_filename = f"trades_{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        trades_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"交易记录已保存到: {csv_filename}")

    returns_analysis = strat.analyzers.returns.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio')
    if sharpe is None or not math.isfinite(float(sharpe)):
        sharpe = annualized_sharpe_from_returns(strat.analyzers.time_return.get_analysis().values())
    annualized_return = returns_analysis.get('rnorm')
    if annualized_return is None or not math.isfinite(float(annualized_return)):
        annualized_return = returns_analysis.get('rtot', 0.0)

    return {
        'final_value': cerebro.broker.getvalue(),
        'sharpe': sharpe,
        'drawdown': strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0),
        'returns': returns_analysis.get('rtot', 0.0),
        'annualized_return': annualized_return,
        'accuracy': accuracy,
        'signal_count': len(strat.trade_signals),
        'trade_count': len(strat.trade_records),
    }


def print_results(label, results):
    print(f"\n=== {label} ===")
    print(f"最终资金: {results['final_value']:.2f}")
    sharpe = results['sharpe']
    print(f"夏普比率: {sharpe:.2f}" if sharpe is not None else "夏普比率: None")
    print(f"最大回撤: {results['drawdown']:.2f}%")
    print(f"总收益率: {results['returns'] * 100:.2f}%")
    print(f"信号准确率: {results['accuracy']:.2f}%")
    print(f"信号数量: {results['signal_count']}")
    print(f"交易次数: {results['trade_count']}")


def main():
    parser = argparse.ArgumentParser(description="R-Breaker 日内策略回测（A股 T+0）")
    parser.add_argument("--symbol", default="603356", help="股票代码，如 603356")
    parser.add_argument("--data-source", choices=["akshare", "tushare"], default="akshare",
                        help="分钟数据源")
    parser.add_argument("--data-folder", default="data", help="tushare 本地缓存目录")
    parser.add_argument("--in-sample-start", default=None, help="样本内起始日期 YYYY-MM-DD (默认：最近交易日往前 30 天)")
    parser.add_argument("--in-sample-end", default=None, help="样本内结束日期 YYYY-MM-DD")
    parser.add_argument("--out-sample-start", default=None, help="样本外起始日期 YYYY-MM-DD")
    parser.add_argument("--tushare-token", default=None, help="tushare token (建议改用环境变量 TUSHARE_TOKEN)")
    parser.add_argument("--plot", action="store_true", help="回测结束后绘制蜡烛图")
    args = parser.parse_args()

    n_days_backtest = 30

    daily_df = get_recent_trading_days_with_prev(args.symbol, n_days_backtest)
    if daily_df.empty or len(daily_df) < n_days_backtest + 1:
        print("错误: 未获取到足够的日线数据来确定回测周期。")
        return

    prev_day_data_row = daily_df.iloc[0]
    in_sample_prev_day_data = (
        prev_day_data_row['最高'], prev_day_data_row['最低'], prev_day_data_row['收盘']
    )
    print(f"回测启动日前一日数据 (来自 {prev_day_data_row['日期'].date()}): "
          f"H={in_sample_prev_day_data[0]}, L={in_sample_prev_day_data[1]}, C={in_sample_prev_day_data[2]}")

    start_date = daily_df.iloc[1]['日期'].strftime('%Y%m%d')
    end_date = daily_df.iloc[-1]['日期'].strftime('%Y%m%d')
    print(f"开始获取分钟数据，范围: {start_date} 至 {end_date}")

    if args.data_source == "tushare":
        min_df = load_or_download_data(args.symbol, start_date, end_date,
                                       args.data_folder, token=args.tushare_token)
    else:
        min_df = load_minute_data_akshare(args.symbol, start_date, end_date)

    if min_df.empty:
        print("错误: 未获取到分钟数据，无法继续回测。")
        return

    if isinstance(min_df.index, pd.DatetimeIndex):
        min_df = min_df.reset_index().rename(columns={'index': '时间'})

    min_df['datetime'] = pd.to_datetime(min_df['时间'])
    min_df.set_index('datetime', inplace=True)

    # 样本内/外区间
    date_series = min_df.index.to_series().dt.date
    if args.in_sample_start and args.in_sample_end:
        in_sample_start = datetime.strptime(args.in_sample_start, '%Y-%m-%d').date()
        in_sample_end = datetime.strptime(args.in_sample_end, '%Y-%m-%d').date()
        in_sample_dates = sorted([d for d in date_series.unique() if in_sample_start <= d <= in_sample_end])
    else:
        in_sample_dates = sorted(date_series.unique())[:-1]

    if args.out_sample_start:
        out_sample_start = datetime.strptime(args.out_sample_start, '%Y-%m-%d').date()
        out_sample_dates = sorted([d for d in date_series.unique() if d >= out_sample_start])
    else:
        out_sample_dates = sorted(date_series.unique())[-1:]

    if not in_sample_dates:
        print("错误: 未找到样本内日期。")
        return

    in_sample_df = min_df[date_series.isin(in_sample_dates)]
    out_sample_df = min_df[date_series.isin(out_sample_dates)]

    print(f"\n样本内优化区间: {in_sample_dates[0]} 至 {in_sample_dates[-1]} (共 {len(in_sample_dates)} 天)")
    if out_sample_dates:
        print(f"样本外测试区间: {out_sample_dates[0]} 至 {out_sample_dates[-1]} (共 {len(out_sample_dates)} 天)")
    else:
        print("警告: 未找到样本外数据。")

    print("\n--- 1. 开始样本内参数优化 ---")
    if bt is None:
        print("未安装 backtrader，无法运行回测。请先执行 uv sync --extra backtest。")
        return
    assert bt is not None
    assert CustomPandasData is not None
    in_sample_data = cast(Any, CustomPandasData)(dataname=in_sample_df)
    best_params, best_results = optimize_strategy(in_sample_data, in_sample_prev_day_data)

    if best_params is None:
        print("参数优化失败，未能找到合适的参数组合。")
        return

    print("\n--- 样本内优化结果 ---")
    print(f"最优参数组合: f1={best_params.f1:.2f}, f2={best_params.f2:.2f}, f3={best_params.f3:.2f}")
    print(f"对应指标: 综合评分={best_results['score']:.2f}, 夏普比率={best_results['sharpe']:.2f}, "
          f"准确率={best_results['accuracy']:.2f}%, 信号数={best_results['signal_count']}")

    if not out_sample_df.empty:
        print("\n--- 2. 开始样本外回测 ---")
        last_in_sample_date = in_sample_dates[-1]
        out_sample_prev_day_df = daily_df[daily_df['日期'].dt.date == last_in_sample_date]

        if out_sample_prev_day_df.empty:
            print(f"错误: 无法找到样本内最后一天 ({last_in_sample_date}) 的日线数据，无法进行样本外测试。")
        else:
            out_sample_prev_day_data = (
                pd.Series(out_sample_prev_day_df['最高']).iloc[0],
                pd.Series(out_sample_prev_day_df['最低']).iloc[0],
                pd.Series(out_sample_prev_day_df['收盘']).iloc[0],
            )
            print(f"样本外测试使用的前一日数据 (来自 {last_in_sample_date}): "
                  f"H={out_sample_prev_day_data[0]:.2f}, L={out_sample_prev_day_data[1]:.2f}, C={out_sample_prev_day_data[2]:.2f}")

            out_sample_data = cast(Any, CustomPandasData)(dataname=out_sample_df)
            out_of_sample_results = run_strategy(
                out_sample_data, best_params, out_sample_prev_day_data,
                save_trades=True, filename_prefix="out_sample")
            print_results("样本外测试结果", out_of_sample_results)

    print("\n--- 3. 运行完整周期回测并绘图 ---")
    full_data = cast(Any, CustomPandasData)(dataname=min_df)
    full_results = run_strategy(
        full_data, best_params, in_sample_prev_day_data,
        plot=args.plot, save_trades=True, filename_prefix="full")
    print_results("完整回测结果 (使用最优参数)", full_results)


if __name__ == '__main__':
    main()
