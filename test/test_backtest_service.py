from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import backtrader as bt
import pandas as pd
import pytest

from backtest import run_backtest_config
from dto.backtest_request import BacktestRequest
from dto.backtest_response import BacktestResponse
from services.backtest_service import get_data, run_backtest_by_request


@pytest.fixture
def frame():
    return pd.DataFrame(
        {
            'open': [100, 100, 110, 120],
            'high': [110, 110, 120, 130],
            'low': [90, 90, 100, 110],
            'close': [100, 100, 110, 120],
            'volume': 100,
        },
        index=pd.date_range('2024-01-01', periods=4),
    )


@pytest.mark.parametrize('slippage, execution_price', [
    ({}, 100),
    ({'slippage_perc': {'perc': 0.02}}, 102),
    ({'slippage_fixed': {'fixed': 3}}, 103),
    ({'slippage_perc': {'perc': 0.02}, 'slippage_fixed': {'fixed': 3}}, 102),
    ({'slippage_perc': {'perc': 0.02, 'slip_open': False}}, 100),
    ({'slippage_fixed': {'fixed': 3, 'slip_open': False}}, 100),
])
def test_broker_settings_affect_execution(frame, slippage, execution_price):
    request = BacktestRequest(
        strategy={'name': 'BuyAndHold'},
        sizer={'name': 'FixedSize', 'params': {'stake': 2}},
        broker={'cash': 1000, 'commission': {'commission': 0.01}, **slippage},
        fromdate=datetime(2024, 1, 1),
        todate=datetime(2024, 1, 4),
    )
    original = request.model_copy(deep=True)
    with patch('services.backtest_service.get_data', return_value=
               bt.feeds.PandasData(dataname=frame)) as load_feed:
        result = run_backtest_by_request(request)

    assert isinstance(result, BacktestResponse)
    assert result.start_cash == 1000
    assert result.end_cash == pytest.approx(1000 - 2 * execution_price * 1.01)
    assert result.end_value == pytest.approx(result.end_cash + 2 * 120)
    assert result.total_return == pytest.approx(100 * (result.end_value / 1000 - 1))
    assert result.closed_trades == 0
    assert result.max_drawdown > 0
    load_feed.assert_called_once_with(request.fromdate, request.todate)
    assert request == original


def test_defaults_and_no_trades_allow_undefined_sharpe(frame):
    request = BacktestRequest(
        strategy={'name': 'BuyAndHold'},
        sizer={'params': {'stake': 0}},
    )
    with patch('services.backtest_service.get_data', return_value=
               bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_by_request(request)

    assert result == BacktestResponse(
        start_cash=10000, end_cash=10000, end_value=10000,
        total_return=0, CAGR=0, sharpe=None, closed_trades=0, max_drawdown=0,
    )


def test_strategy_parameters_and_analyzers_match_config_runner():
    prices = [10, 11, 12, 13, 12, 11, 10, 9, 10, 11, 12, 13,
              14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11]
    frame = pd.DataFrame(
        {name: prices for name in ('open', 'high', 'low', 'close')},
        index=pd.date_range('2024-01-01', periods=len(prices)),
    )
    request = BacktestRequest(strategy={
        'name': 'MACrossOver', 'params': {'fast': 2, 'slow': 3, 'movav': 'EMA'},
    })
    with patch('services.backtest_service.get_data', return_value=
               bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_by_request(request)
    config = request.model_dump(exclude_none=True)
    config['data'] = {'path': 'prices.csv'}
    with patch('backtest.feed_from_conf', return_value=
               bt.feeds.PandasData(dataname=frame)):
        expected = run_backtest_config(config)

    assert result.model_dump() == expected
    assert result.closed_trades > 0
    assert result.sharpe is not None


@pytest.mark.parametrize('overrides', [
    {'strategy': {'name': 'missing'}},
    {'strategy': {'name': 'MACrossOver', 'params': {'movav': 'missing'}}},
    {'strategy': {'name': 'BuyAndHold', 'params': {'typo': 1}}},
    {'sizer': {'name': 'missing'}},
    {'sizer': {'name': 'FixedSize', 'params': {'typo': 1}}},
])
def test_invalid_parameters_fail_before_loading_data(overrides):
    request = BacktestRequest.model_validate({
        'strategy': {'name': 'BuyAndHold'}, **overrides,
    })
    with patch('services.backtest_service.get_data') as load_feed:
        with pytest.raises(ValueError):
            run_backtest_by_request(request)
        load_feed.assert_not_called()


def test_data_path_is_independent_of_working_directory(frame, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_frame = frame.rename_axis('date').reset_index()
    start = datetime(2024, 1, 2)
    end = datetime(2024, 1, 3)
    with patch('services.backtest_service.pd.read_csv', return_value=csv_frame) as read:
        feed = get_data(start, end)

    read.assert_called_once_with(Path(__file__).resolve().parents[1] / 'data' / 'AAPL.csv')
    cerebro = bt.Cerebro()
    cerebro.adddata(feed)
    cerebro.run()
    assert len(feed) == 2
    assert feed.datetime.datetime(0) == end
