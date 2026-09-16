from datetime import datetime
from typing import Any

import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
from pandas import DataFrame

from registry import strategy_by_name, sizer_by_name


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

def datetime_from_conf(date_conf: dict[str, Any] | None) -> datetime | None:
    if date_conf is None:
        return None

    return datetime(
        year=date_conf['year'],
        month=date_conf['month'],
        day=date_conf['day']
    )

def feed_from_conf(data_conf: dict[str, Any]) -> bt.feeds.PandasData:
    df = pd.read_csv(data_conf['path'])
    data = bt.feeds.PandasData(
        dataname=df,
        fromdate=datetime_from_conf(data_conf.get('fromdate', None)),
        todate=datetime_from_conf(data_conf.get('todate', None)),
        open=data_conf.get('open', -1),
        high=data_conf.get('high', -1),
        low=data_conf.get('low', -1),
        close=data_conf.get('close', -1),
        volume=data_conf.get('volume', -1),
        openinterest=data_conf.get('openinterest', -1)
    )
    return data

def run_backtest_config(config: dict[str, Any]) -> dict[str, Any]:
    cerebro = bt.Cerebro()
    cerebro.adddata(feed_from_conf(config['data']))
    cerebro.addstrategy(
        strategy_by_name(config['strategy']['name']),
        **config['strategy'].get('params', {})
    )
    if 'sizer' in config:
        cerebro.addsizer(
            sizer_by_name(config['sizer']['name']),
            **config['sizer'].get('params', {})
        )

    broker_conf = config.get('broker', {})
    cash = broker_conf.get('cash', 10000.0)
    cerebro.broker.set_cash(cash)

    if 'slippage_perc' in broker_conf:
        cerebro.broker.set_slippage_perc(**config['broker']['slippage_perc'])
    elif 'slippage_fixed' in broker_conf:
        cerebro.broker.set_slippage_fixed(**config['broker']['slippage_fixed'])

    if 'commission' in broker_conf:
        cerebro.broker.setcommission(**config['broker']['commission'])

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
        'CAGR': strat.analyzers['returns'].get_analysis().rnorm100,
        'sharpe': strat.analyzers['sharpe'].get_analysis()['sharperatio'],
        'closed_trades': strat.analyzers['trades'].get_analysis().total.closed,
        'max_drawdown': strat.analyzers['drawdown'].get_analysis().max.drawdown,
    }