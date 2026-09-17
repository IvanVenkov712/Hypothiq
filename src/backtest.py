from datetime import datetime
from typing import Any

import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
from pandas import DataFrame

from dto.backtest_request import BacktestRequest
from dto.backtest_response import BacktestResponse
from registry import resolve_params, strategy_by_name, sizer_by_name

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
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
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
    strategy = strategy_by_name(config['strategy']['name'])
    strategy_params = resolve_params(strategy, config['strategy'].get('params', {}))
    if 'sizer' in config:
        sizer = sizer_by_name(config['sizer']['name'])
        sizer_params = resolve_params(sizer, config['sizer'].get('params', {}))

    cerebro = bt.Cerebro()
    cerebro.adddata(feed_from_conf(config['data']))
    cerebro.addstrategy(strategy, **strategy_params)
    if 'sizer' in config:
        cerebro.addsizer(sizer, **sizer_params)

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
        'CAGR': strat.analyzers.returns.get_analysis()['rnorm100'],
        'sharpe': strat.analyzers.sharpe.get_analysis()['sharperatio'],
        'closed_trades': strat.analyzers.trades.get_analysis().get('total', {}).get('closed', 0),
        'max_drawdown': strat.analyzers.drawdown.get_analysis().max.drawdown,
    }