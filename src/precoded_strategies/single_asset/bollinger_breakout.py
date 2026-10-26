"""Bollinger squeeze-breakout research strategy for Backtrader.

Install: python -m pip install backtrader==1.9.78.123 pandas
Run:     python bollinger_breakout.py prices.csv
Shorts:  python bollinger_breakout.py prices.csv --allow-short
CSV:     date,open,high,low,close,volume (ascending, unique daily dates)

Operational definitions (configurable, not universal Bollinger rules):
  squeeze:     BandWidth <= the 20th percentile of the PRIOR 120 widths,
               for 3 consecutive bars; each bar uses its own prior window.
  expansion:   BandWidth grows by at least 5% from the previous bar.
  continuation: after a qualified breakout, price stays on its favorable
               side of the middle band, without confirmed contraction.
  contraction: BandWidth decreases for 3 consecutive comparisons.

These flags can overlap. BandWidth = (upper - lower) / middle.
An earlier confirmed squeeze arms entry while it persists and for 10 bars
afterward. One signal consumes that setup; a new squeeze episode is needed
to rearm. Entry requires expansion AND a fresh closing-price cross outside
an outer band. Long-only by default; optional mirrored short entries.

Exit on middle-band failure, contraction (optional), or a 5% adverse CLOSE
relative to the position's average fill (optional). This loss threshold is
NOT a resting stop order or a bound on losses. All orders are market orders
created after a completed bar; normally they fill at the next bar's open.

Scope: one positive-priced instrument, ordinary historical bars, one strategy
owning the position, default full-fill backtesting broker. Sizing belongs to
Backtrader's sizer. The example allocates 20% of cash, with 0.1% commission
per side and 0.05% configured slippage. These are illustrative assumptions.
No pyramiding, automatic reversal, intrabar protection, live execution
management, or forced final liquidation. Short borrow/recall costs, spread,
market impact, taxes and corporate-action cash flows are not modeled here.
Short availability and realistic short margin rules require separate broker
configuration. The strategy's optional short switch does not supply them.
The 20-bar bands plus 120 prior widths require 140 bars before evaluation;
squeeze confirmation and next-open execution require additional bars.
Parameters are research hypotheses, not optimized or validated profitability
claims. Validate on held-out periods with realistic data, costs and sizing.
Normalized BandWidth can fall in a healthy trend; contraction is not proof
of a price reversal. False breakouts can consume a setup and miss a later move.

Inspect strategy.latest, strategy.history and strategy.order_events.
history contains only bars with complete indicator/reference history.
The prior-window quantile costs O(lookback * log(lookback)) per bar.

Sources:
https://www.bollingerbands.com/bollinger-band-rules
https://www.backtrader.com/docu/indautoref/#bollingerbands
https://www.backtrader.com/docu/order/
"""

import argparse
from collections import deque
import math

import backtrader as bt
import backtrader.indicators as btind


def quantile(values, q):
    """Linear interpolation, with q in [0, 1]."""
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


class BollingerBreakout(bt.Strategy):
    params = dict(
        period=20,
        devfactor=2.0,
        squeeze_lookback=120,
        squeeze_quantile=0.20,
        squeeze_bars=3,
        entry_window=10,
        expansion_rate=0.05,
        contraction_bars=3,
        exit_on_contraction=True,
        stop_loss=0.05,  # None disables this CLOSE-based exit.
        allow_short=False,
        record_history=True,
        printlog=False,
    )

    def __init__(self):
        if len(self.datas) != 1:
            raise ValueError("This strategy requires exactly one data feed")
        for name, minimum in (
            ("period", 2), ("squeeze_lookback", 2), ("squeeze_bars", 1),
            ("entry_window", 1), ("contraction_bars", 1),
        ):
            value = getattr(self.p, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if not math.isfinite(self.p.devfactor) or self.p.devfactor <= 0:
            raise ValueError("devfactor must be finite and positive")
        if not 0 <= self.p.squeeze_quantile <= 1:
            raise ValueError("squeeze_quantile must be in [0, 1]")
        if not math.isfinite(self.p.expansion_rate) or self.p.expansion_rate <= 0:
            raise ValueError("expansion_rate must be finite and positive")
        if self.p.stop_loss is not None and not 0 < self.p.stop_loss < 1:
            raise ValueError("stop_loss must be None or a fraction in (0, 1)")

        self.bands = btind.BollingerBands(
            self.data.close, period=self.p.period, devfactor=self.p.devfactor,
            movav=btind.MovingAverageSimple,
        )
        self._widths = deque(maxlen=self.p.squeeze_lookback)
        self._low_count = 0
        self._fall_count = 0
        self._was_squeeze = False
        self._setup_consumed = False
        self._armed_until = None
        self._direction = 0  # Qualified breakout direction, independent of fills.
        self._exit_reason = None  # Latch an exit until actually flat.
        self.order = None
        self.is_squeeze = False
        self.is_expansion = False
        self.is_continuation = False
        self.is_contraction = False
        self.latest = None
        self.history = []
        self.order_events = []

    def _observe(self):
        """Update signals even while an order is pending; use no future bars."""
        close = float(self.data.close[0])
        middle = float(self.bands.mid[0])
        upper = float(self.bands.top[0])
        lower = float(self.bands.bot[0])
        if not all(math.isfinite(x) for x in (close, middle, upper, lower)):
            raise ValueError("Non-finite price/band: clean the input data")
        if close <= 0 or middle <= 0:
            raise ValueError("This strategy requires positive prices")
        width = max(0.0, (upper - lower) / middle)

        if len(self._widths) < self.p.squeeze_lookback:
            self._widths.append(width)
            return None

        # The current width is appended ONLY after evaluating the prior window.
        previous_width = self._widths[-1]
        threshold = quantile(self._widths, self.p.squeeze_quantile)
        self._low_count = self._low_count + 1 if width <= threshold else 0
        self._fall_count = (
            self._fall_count + 1 if width < previous_width - 1e-12 else 0
        )
        self.is_squeeze = self._low_count >= self.p.squeeze_bars
        # If the prior width is zero, require a nontrivial positive width.
        self.is_expansion = (
            width > previous_width + 1e-12
            and width >= previous_width * (1 + self.p.expansion_rate)
        )
        self.is_contraction = self._fall_count >= self.p.contraction_bars

        bar = len(self)
        armed_before_this_bar = (
            self._armed_until is not None and bar <= self._armed_until
        )
        crossed_up = (
            close > upper and self.data.close[-1] <= self.bands.top[-1]
        )
        crossed_down = (
            close < lower and self.data.close[-1] >= self.bands.bot[-1]
        )
        signal = 0
        if armed_before_this_bar and self.is_expansion:
            signal = 1 if crossed_up else (-1 if crossed_down else 0)

        # Continuation uses the direction established on an EARLIER bar.
        trend_intact = self._direction * (close - middle) > 0
        self.is_continuation = bool(trend_intact and not self.is_contraction)
        if not trend_intact or self.is_contraction:
            self._direction = 0

        if signal:
            self._direction = signal
            self.is_continuation = False
            self._armed_until = None
            self._setup_consumed = True
        else:
            if self.is_squeeze:
                if not self._was_squeeze:
                    self._setup_consumed = False
                if not self._setup_consumed:
                    self._armed_until = bar + self.p.entry_window
            elif self._armed_until is not None and bar > self._armed_until:
                self._armed_until = None

        self._was_squeeze = self.is_squeeze
        self._widths.append(width)
        row = dict(
            date=self.data.datetime.datetime(0).isoformat(),
            close=close, middle=middle, upper=upper, lower=lower,
            bandwidth=width, squeeze_threshold=threshold,
            squeeze=self.is_squeeze, expansion=self.is_expansion,
            continuation=self.is_continuation, contraction=self.is_contraction,
            direction=self._direction, breakout_signal=signal,
            position=self.position.size, action="hold",
        )
        self.latest = row
        if self.p.record_history:
            self.history.append(row)
        return row

    def next(self):
        row = self._observe()
        if row is None:
            return

        # Exit rules use the actual position, not the signal's assumed direction.
        if self.position:
            side = 1 if self.position.size > 0 else -1
            position_return = side * (row["close"] / self.position.price - 1)
            if self.p.stop_loss is not None and position_return <= -self.p.stop_loss:
                self._exit_reason = "close_loss_threshold"
            elif side * (row["close"] - row["middle"]) <= 0:
                self._exit_reason = "middle_band_failure"
            elif self.p.exit_on_contraction and self.is_contraction:
                self._exit_reason = "contraction"
        else:
            self._exit_reason = None

        # Submitted, accepted and partially filled orders keep this reference.
        if self.order is not None:
            row["action"] = "pending"
            return

        if self.position:
            if self._exit_reason:
                self.order = self.close(exectype=bt.Order.Market)
                row["action"] = "exit:" + self._exit_reason
        elif row["breakout_signal"] == 1:
            self.order = self.buy(exectype=bt.Order.Market)
            row["action"] = "enter_long" if self.order is not None else "zero_size"
        elif row["breakout_signal"] == -1 and self.p.allow_short:
            self.order = self.sell(exectype=bt.Order.Market)
            row["action"] = "enter_short" if self.order is not None else "zero_size"

    def notify_order(self, order):
        event = dict(
            date=self.data.datetime.datetime(0).isoformat(),
            ref=order.ref, status=order.getstatusname(),
            size=order.executed.size, price=order.executed.price,
            commission=order.executed.comm,
        )
        self.order_events.append(event)
        if self.p.printlog:
            print(event)
        if order.status in (order.Submitted, order.Accepted, order.Partial):
            return
        if self.order is not None and self.order.ref == order.ref:
            self.order = None


def main():
    """Minimal daily-data runner; import the class for your own Cerebro setup."""
    import pandas as pd

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="Daily CSV: date,open,high,low,close,volume")
    parser.add_argument("--allow-short", action="store_true")
    parser.add_argument("--cash", type=float, default=10000.0)
    parser.add_argument("--allocation", type=float, default=20.0,
                        help="Percent of cash per entry; default 20")
    parser.add_argument("--commission", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.cash) or args.cash <= 0 or not 0 < args.allocation < 100:
        parser.error("Use positive cash and an allocation strictly between 0 and 100")
    if not 0 <= args.commission < 1 or not 0 <= args.slippage < 1:
        parser.error("Commission and slippage must be fractions in [0, 1)")

    frame = pd.read_csv(args.csv, index_col="date", parse_dates=["date"])
    required = ["open", "high", "low", "close", "volume"]
    if not set(required) <= set(frame.columns):
        parser.error("CSV must contain date,open,high,low,close,volume")
    if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans
            or not frame.index.is_unique or not frame.index.is_monotonic_increasing):
        parser.error("Dates must be valid, unique and sorted ascending")
    frame = frame[required].apply(pd.to_numeric, errors="raise")
    if not all(math.isfinite(x) for x in frame.to_numpy().ravel()):
        parser.error("Data must contain only finite OHLCV values")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        parser.error("OHLC prices must be positive")
    if ((frame.high < frame[["open", "close", "low"]].max(axis=1)).any()
            or (frame.low > frame[["open", "close"]].min(axis=1)).any()
            or (frame.volume < 0).any()):
        parser.error("Invalid OHLC ranges or negative volume")
    if len(frame) < 20 + 120 + 3:
        parser.error("Provide at least 143 daily bars; use much more for evaluation")

    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=frame, timeframe=bt.TimeFrame.Days))
    cerebro.addstrategy(BollingerBreakout, allow_short=args.allow_short, printlog=args.log)
    cerebro.addsizer(bt.sizers.PercentSizerInt, percents=args.allocation)
    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(commission=args.commission)
    cerebro.broker.set_slippage_perc(args.slippage, slip_open=True)
    cerebro.broker.set_coc(False)
    cerebro.broker.set_coo(False)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    strategy = cerebro.run()[0]

    final_value = cerebro.broker.getvalue()
    trades = strategy.analyzers.trades.get_analysis()
    closed = trades.get("total", {}).get("closed", 0)
    print(f"Final marked-to-market equity: {final_value:.2f}")
    print(f"Total return: {100 * (final_value / args.cash - 1):.2f}%")
    print(f"Sharpe ratio: {strategy.analyzers.sharpe.get_analysis()['sharperatio']}")
    print(f"Maximum drawdown: {strategy.analyzers.drawdown.get_analysis().max.drawdown:.2f}%")
    print(f"Closed trades: {closed}; open position: {strategy.position.size}")
    print(f"Pending order at end: {strategy.order is not None}")
    print("Detected bars:", {
        phase: sum(row[phase] for row in strategy.history)
        for phase in ("squeeze", "expansion", "continuation", "contraction")
    })

if __name__ == "__main__":
    main()
