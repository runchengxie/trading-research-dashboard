"""Backtrader strategy implementation for R-Breaker.

The CLI and research runners remain in the rbreaker module.
"""

from __future__ import annotations

from datetime import time
from typing import Any, cast

from trading_research.strategies.rbreaker_math import calculate_levels

try:
    import backtrader as bt
except ImportError:  # pragma: no cover
    bt = None


def is_session_close_or_later(current_time: time, close_hour: int, close_minute: int) -> bool:
    """Return whether new signals must be blocked for the current session."""

    return current_time >= time(close_hour, close_minute)

if bt is not None:
    class CustomPandasData(bt.feeds.PandasData):
        """自定义数据源，以匹配中文列名。"""

        params = (
            ('datetime', None),
            ('open', '开盘'),
            ('high', '最高'),
            ('low', '最低'),
            ('close', '收盘'),
            ('volume', '成交量'),
            ('openinterest', None),
        )


    class RBreakerStrategy(bt.Strategy):
        """
        R-Breaker 交易策略 (优化版，来自 t.py)。

        核心逻辑:
        1. 每日开盘前，根据前一日最高价(H)、最低价(L)、收盘价(C)计算六个关键价位。
        2. 根据当前价格与这六个价位的关系产生交易信号 (趋势突破、反转确认、日内止损)。
        3. 每日收盘前强制平仓，不持仓隔夜。
        4. 正确地在多日回测中滚动更新前一日的数据。
        """

        params = (
            ('f1', 0.35),
            ('f2', 0.07),
            ('f3', 0.25),
            ('reverse', 2.0),      # 止损百分比
            ('rangemin', 0.5),     # 前一日价格波动幅度下限
            ('eval_period', 10),   # 信号评估周期（分钟）
            ('session_close_hour', 14),
            ('session_close_minute', 55),
            ('printlog', False),
            # 用于初始化回测的第一个交易日
            ('prev_day_high', 0.0),
            ('prev_day_low', 0.0),
            ('prev_day_close', 0.0),
        )

        def __init__(self):
            self.last_date = None
            self.today_high = 0.0
            self.today_low = 0.0
            self.order = None
            self.stop_order = None
            self.trade_signals = []
            self.trade_records = []

            self.ssetup, self.bsetup = 0, 0
            self.senter, self.benter = 0, 0
            self.bbreak, self.sbreak = 0, 0

        def log(self, txt, dt=None, doprint=False):
            if self.p.printlog or doprint:
                dt = dt or self.datas[0].datetime.datetime(0)
                print(f'{dt.strftime("%Y-%m-%d %H:%M:%S")} | {txt}')

        def calculate_levels(self, H, L, C):
            if H <= L:
                return
            (
                self.ssetup,
                self.bsetup,
                self.senter,
                self.benter,
                self.bbreak,
                self.sbreak,
            ) = calculate_levels(H, L, C, f1=self.p.f1, f2=self.p.f2, f3=self.p.f3)

        def notify_order(self, order):
            if order.status in [order.Submitted, order.Accepted]:
                return

            if order.status in [order.Completed]:
                if order.isbuy():
                    self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}, Cost: {order.executed.value:.2f}')
                    self.trade_records.append({
                        'datetime': self.data.datetime.datetime(0),
                        'action': 'BUY',
                        'price': order.executed.price,
                        'size': order.executed.size,
                        'value': order.executed.value,
                        'commission': order.executed.comm,
                        'pnl': 0.0,
                    })
                elif order.issell():
                    self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}, Cost: {order.executed.value:.2f}')
                    self.trade_records.append({
                        'datetime': self.data.datetime.datetime(0),
                        'action': 'SELL',
                        'price': order.executed.price,
                        'size': order.executed.size,
                        'value': order.executed.value,
                        'commission': order.executed.comm,
                        'pnl': 0.0,
                    })

                if self.order == order:
                    self.order = None

            elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                self.log(f'Order Canceled/Margin/Rejected: {order.getstatusname()}')

            if not order.alive():
                if order == self.stop_order:
                    self.stop_order = None
                elif self.order == order:
                    self.order = None

        def next(self):
            current_date = self.data.datetime.date(0)

            if current_date != self.last_date:
                if self.last_date is None:
                    H, L, C = self.p.prev_day_high, self.p.prev_day_low, self.p.prev_day_close
                    self.log(f'首日初始化: 使用外部传入数据 H={H:.2f}, L={L:.2f}, C={C:.2f}')
                else:
                    H, L, C = self.today_high, self.today_low, self.data.close[-1]
                    self.log(f'新交易日 {current_date}: 使用前一日数据 H={H:.2f}, L={L:.2f}, C={C:.2f}')

                self.calculate_levels(H, L, C)
                self.today_high = self.data.high[0]
                self.today_low = self.data.low[0]
                self.last_date = current_date
            else:
                self.today_high = max(self.today_high, self.data.high[0])
                self.today_low = min(self.today_low, self.data.low[0])

            if self.order:
                return

            if is_session_close_or_later(
                self.data.datetime.time(),
                self.p.session_close_hour,
                self.p.session_close_minute,
            ):
                self.close_positions()
                return

            prev_day_range = self.ssetup - self.bsetup
            if prev_day_range >= self.p.rangemin:
                self.check_signals()

            self.evaluate_signals()

        def check_signals(self):
            price = self.data.close[0]

            if not self.position:
                if price > self.bbreak:
                    self.order = self.buy()
                    self.record_signal('Long', price, self.data.datetime.datetime(0))
                elif price < self.sbreak:
                    self.order = self.sell()
                    self.record_signal('Short', price, self.data.datetime.datetime(0))
            else:
                if self.position.size > 0:
                    if self.today_high > self.ssetup and price < self.senter:
                        self.order = self.close()
                        self.order = self.sell()
                        self.record_signal('Reverse to Short', price, self.data.datetime.datetime(0))
                elif self.position.size < 0:
                    if self.today_low < self.bsetup and price > self.benter:
                        self.order = self.close()
                        self.order = self.buy()
                        self.record_signal('Reverse to Long', price, self.data.datetime.datetime(0))

            if self.position and not self.stop_order:
                if self.position.size > 0:
                    stop_price = self.position.price * (1 - self.p.reverse / 100)
                    self.stop_order = self.sell(exectype=cast(Any, bt).Order.Stop, price=stop_price)
                else:
                    stop_price = self.position.price * (1 + self.p.reverse / 100)
                    self.stop_order = self.buy(exectype=cast(Any, bt).Order.Stop, price=stop_price)

        def close_positions(self):
            if self.position:
                self.log(f'收盘前平仓, 当前仓位: {self.position.size}')
                self.order = self.close()
                if self.stop_order:
                    self.cancel(self.stop_order)

        def record_signal(self, signal_type, price, time):
            self.trade_signals.append({'type': signal_type, 'price': price, 'time': time, 'evaluated': False})

        def evaluate_signals(self):
            current_price = self.data.close[0]
            current_time = self.data.datetime.datetime(0)
            for signal in self.trade_signals:
                if not signal['evaluated']:
                    time_diff = (current_time - signal['time']).total_seconds() / 60
                    if time_diff >= self.p.eval_period:
                        price_diff = current_price - signal['price']
                        correct = (price_diff > 0) if 'Long' in signal['type'] else (price_diff < 0)
                        signal.update({'evaluated': True, 'outcome': 'Correct' if correct else 'Incorrect'})

        def stop(self):
            evaluated_signals = [s for s in self.trade_signals if s['evaluated']]
            if evaluated_signals:
                correct_count = sum(1 for s in evaluated_signals if s['outcome'] == 'Correct')
                accuracy = correct_count / len(evaluated_signals) * 100
                self.log(f"信号准确率分析: {accuracy:.2f}% ({correct_count}/{len(evaluated_signals)} 个信号正确)", doprint=True)
            else:
                self.log("无已评估的交易信号可供分析。", doprint=True)


else:
    CustomPandasData = None
    RBreakerStrategy = None
