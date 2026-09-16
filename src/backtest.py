from typing import Any

import backtrader as bt
import backtrader.analyzers as btanalyzers
from pandas import DataFrame


def run_backtest_single_asset(
        frame: DataFrame,
        strategy,
        *,
        cash: float = 10000.0,
        strategy_params: dict[str, Any] | None = None,
        sizer=bt.sizers.FixedSize,
        sizer_params: dict[str, Any] | None = None,
        slip_perc: float = 0.0,
        slip_open: bool = False,
        slip_match: bool = True,
        slip_limit: bool = True,
        slip_out: bool = False,
        comm_perc: float = 0.0

) -> dict[str, Any]:
    if strategy_params is None:
        strategy_params = {}
    if sizer_params is None:
        sizer_params = {}

    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=frame, timeframe=bt.TimeFrame.Days))
    cerebro.addstrategy(strategy, **strategy_params)
    cerebro.addsizer(sizer, **sizer_params)
    cerebro.broker.cash = cash
    cerebro.broker.set_slippage_perc(
        perc=slip_perc,
        slip_open=slip_open,
        slip_match=slip_match,
        slip_limit=slip_limit,
        slip_out=slip_out
    )
    cerebro.broker.setcommission(commission=comm_perc)
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    cerebro.addanalyzer(
        btanalyzers.SharpeRatio,
        _name="sharpe",
        timeframe=bt.TimeFrame.Days,
        annualize=True,
        riskfreerate=0.0,
    )
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')

    strats = cerebro.run()
    strat = strats[0]
    return {
        'start_cash': cash,
        'end_cash': cerebro.broker.cash,
        'end_value': cerebro.broker.get_value(),
        'total_return': 100 * (cerebro.broker.getvalue() / cash - 1),
        'CAGR': strat.analyzers['returns'].get_analysis().rnorm,
        'sharpe': strat.analyzers['sharpe'].get_analysis()['sharperatio'],
        'closed_trades': strat.analyzers['trades'].get_analysis(),
        'max_drawdown': strat.analyzers['drawdown'].get_analysis().max.drawdown,
    }
