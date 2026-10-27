from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import backtrader as bt
import pandas as pd
import pytest

from dto.backtest_request import BacktestRequest, DataRequest
from dto.backtest_response import BacktestResponse
from services.backtest_service import get_data, get_data_y_finance, run_backtest_by_request


@pytest.fixture
def data_request():
    return DataRequest(
        ticker='AAPL',
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 4),
    )


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
def test_broker_settings_affect_execution(frame, data_request, slippage, execution_price):
    request = BacktestRequest(
        strategy={'name': 'BuyAndHold'},
        sizer={'name': 'FixedSize', 'params': {'stake': 2}},
        broker={'cash': 1000, 'commission': {'commission': 0.01}, **slippage},
        data_request=data_request,
    )
    original = request.model_copy(deep=True)
    with patch('services.backtest_service.get_data_y_finance', return_value=
               bt.feeds.PandasData(dataname=frame)) as load_feed:
        result = run_backtest_by_request(request)

    assert isinstance(result, BacktestResponse)
    assert result.start_cash == 1000
    assert result.end_cash == pytest.approx(1000 - 2 * execution_price * 1.01)
    assert result.end_value == pytest.approx(result.end_cash + 2 * 120)
    assert result.total_return == pytest.approx(100 * (result.end_value / 1000 - 1))
    assert result.closed_trades == 0
    assert result.max_drawdown > 0
    load_feed.assert_called_once_with(request.data_request)
    assert request == original


def test_defaults_and_no_trades_allow_undefined_sharpe(frame, data_request):
    request = BacktestRequest(
        strategy={'name': 'BuyAndHold'},
        data_request=data_request,
        sizer={'params': {'stake': 0}},
    )
    with patch('services.backtest_service.get_data_y_finance', return_value=
               bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_by_request(request)

    assert result == BacktestResponse(
        start_cash=10000, end_cash=10000, end_value=10000,
        total_return=0, CAGR=0, sharpe=None, closed_trades=0, max_drawdown=0,
        history=[
            {
                'time': timestamp.isoformat(),
                'cash': 10000,
                'equity': 10000,
                'drawdown': 0,
            }
            for timestamp in frame.index
        ],
    )


@pytest.mark.parametrize('overrides', [
    {'strategy': {'name': 'missing'}},
    {'strategy': {'name': 'MACrossOver', 'params': {'movav': 'missing'}}},
    {'strategy': {'name': 'BuyAndHold', 'params': {'typo': 1}}},
    {'sizer': {'name': 'missing'}},
    {'sizer': {'name': 'FixedSize', 'params': {'typo': 1}}},
])
def test_invalid_parameters_fail_before_loading_data(overrides, data_request):
    request = BacktestRequest.model_validate({
        'strategy': {'name': 'BuyAndHold'}, 'data_request': data_request, **overrides,
    })
    with patch('services.backtest_service.get_data_y_finance') as load_feed:
        with pytest.raises(ValueError):
            run_backtest_by_request(request)
        load_feed.assert_not_called()


def test_yfinance_download_uses_requested_symbol_interval_and_dates(frame, data_request):
    request = data_request.model_copy(update={
        'start': datetime(2024, 1, 2),
        'end': datetime(2024, 1, 3),
        'interval': '1wk',
    })
    with patch('services.backtest_service.yf.download', return_value=frame) as download:
        feed = get_data_y_finance(request)

    download.assert_called_once_with(
        tickers=request.ticker,
        interval=request.interval,
        start=request.start,
        end=request.end,
        multi_level_index=False,
    )
    cerebro = bt.Cerebro()
    cerebro.adddata(feed)
    cerebro.run()
    assert len(feed) == 2
    assert feed.datetime.datetime(0) == request.end


@pytest.mark.parametrize('downloaded, message', [
    (None, 'An error occurred during yfinance data download'),
    (pd.DataFrame(), 'There are no records'),
])
def test_yfinance_rejects_missing_data(data_request, downloaded, message):
    with patch('services.backtest_service.yf.download', return_value=downloaded):
        with pytest.raises(ValueError, match=message):
            get_data_y_finance(data_request)


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
