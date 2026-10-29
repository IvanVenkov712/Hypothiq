import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import backtrader as bt
import pandas as pd
import pytest

from dto.backtest_request import BacktestRequest, DataRequest
from dto.backtest_response import BacktestResponse
from main import app
from services.backtest_service import run_backtest_by_request
from services.market_data import MarketDataError, get_data, get_data_y_finance


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
            'Open': [100, 100, 110, 120],
            'High': [110, 110, 120, 130],
            'Low': [90, 90, 100, 110],
            'Close': [100, 100, 110, 120],
            'Volume': 100,
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


@pytest.mark.parametrize('bars', [1, 4])
def test_defaults_and_no_trades_allow_undefined_sharpe(frame, data_request, bars):
    frame = frame.iloc[:bars]
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
                'close': close,
                'cash': 10000,
                'equity': 10000,
                'drawdown': 0,
            }
            for timestamp, close in frame['Close'].items()
        ],
    )


@pytest.mark.parametrize('commission', [0, 0.01])
def test_history_tracks_equity_drawdown_and_execution_costs(data_request, commission):
    prices = [100, 100, 120, 90, 130, 110]
    frame = pd.DataFrame(
        {'open': prices, 'high': prices, 'low': prices, 'close': prices, 'volume': 100},
        index=pd.bdate_range('2024-01-04', periods=len(prices)),
    )
    request = BacktestRequest(
        strategy={'name': 'BuyAndHold'},
        data_request=data_request.model_copy(update={
            'start': frame.index[0].to_pydatetime(),
            'end': (frame.index[-1] + pd.Timedelta(days=1)).to_pydatetime(),
        }),
        broker={'cash': 1000, 'commission': {'commission': commission}},
        sizer={'name': 'FixedSize', 'params': {'stake': 2}},
    )
    with patch('services.backtest_service.get_data_y_finance', return_value=
               bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_by_request(request)

    fee = 200 * commission
    expected_equity = [1000, 1000 - fee, 1040 - fee, 980 - fee, 1060 - fee, 1020 - fee]
    expected_drawdown = [0, fee / 1000 * 100, 0, 60 / (1040 - fee) * 100,
                         0, 40 / (1060 - fee) * 100]
    assert [point.time for point in result.history] == list(frame.index.to_pydatetime())
    assert [point.close for point in result.history] == prices
    assert [point.cash for point in result.history] == pytest.approx([1000] + [800 - fee] * 5)
    assert [point.equity for point in result.history] == pytest.approx(expected_equity)
    assert [point.drawdown for point in result.history] == pytest.approx(expected_drawdown)
    assert result.history[-1].cash == result.end_cash
    assert result.history[-1].equity == result.end_value
    assert max(point.drawdown for point in result.history) == pytest.approx(result.max_drawdown)
    assert result.total_return == pytest.approx(100 * (result.history[-1].equity / result.start_cash - 1))
    assert result.closed_trades == 0


def test_history_includes_indicator_warmup_bars(frame, data_request):
    request = BacktestRequest(
        strategy={'name': 'MACrossOver', 'params': {'fast': 2, 'slow': 3}},
        data_request=data_request,
    )
    with patch('services.backtest_service.get_data_y_finance', return_value=
               bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_by_request(request)

    # The crossover needs four bars; the first three must still reach the chart.
    assert [point.time for point in result.history] == list(frame.index.to_pydatetime())
    assert [point.close for point in result.history] == list(frame['Close'])
    assert [point.cash for point in result.history] == [result.start_cash] * len(frame)
    assert [point.equity for point in result.history] == [result.start_cash] * len(frame)
    assert [point.drawdown for point in result.history] == [0] * len(frame)


def test_backtest_endpoint_returns_typed_history_as_json(frame, data_request):
    request = BacktestRequest(
        strategy={'name': 'BuyAndHold'},
        data_request=data_request.model_copy(update={'end': datetime(2024, 1, 5)}),
    )
    messages = []

    async def receive():
        return {'type': 'http.request', 'body': request.model_dump_json().encode(),
                'more_body': False}

    async def send(message):
        messages.append(message)

    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': 'POST',
        'scheme': 'http',
        'path': '/backtests/run-backtest',
        'root_path': '',
        'query_string': b'',
        'headers': [(b'content-type', b'application/json')],
    }
    with patch('services.market_data.yf.download', return_value=frame):
        asyncio.run(app(scope, receive, send))

    assert messages[0]['status'] == 200
    assert (b'content-type', b'application/json') in messages[0]['headers']
    body = b''.join(message.get('body', b'') for message in messages[1:])
    payload = json.loads(body)
    assert payload['history'] == [
        {'time': timestamp.isoformat(), 'close': close, 'cash': cash,
         'equity': equity, 'drawdown': 0}
        for timestamp, close, cash, equity in zip(
            frame.index, frame['Close'], [10000, 9900, 9900, 9900],
            [10000, 10000, 10010, 10020],
        )
    ]
    assert payload['history'][-1]['cash'] == payload['end_cash']
    assert payload['history'][-1]['equity'] == payload['end_value']


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
    })
    with patch('services.market_data.yf.download', return_value=frame) as download:
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
    assert len(feed) == 1
    assert feed.datetime.datetime(0) == request.start
    assert feed._timeframe == bt.TimeFrame.Days
    assert feed._compression == 1


@pytest.mark.parametrize('downloaded, error, message', [
    (None, MarketDataError, 'provider returned no response'),
    (pd.DataFrame(), ValueError, 'No daily prices were returned'),
])
def test_yfinance_rejects_missing_data(data_request, downloaded, error, message):
    with patch('services.market_data.yf.download', return_value=downloaded):
        with pytest.raises(error, match=message):
            get_data_y_finance(data_request)


def test_data_path_is_independent_of_working_directory(frame, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_frame = frame.rename_axis('date').reset_index()
    start = datetime(2024, 1, 2)
    end = datetime(2024, 1, 3)
    with patch('services.market_data.pd.read_csv', return_value=csv_frame) as read:
        feed = get_data(start, end)

    read.assert_called_once_with(Path(__file__).resolve().parents[1] / 'data' / 'AAPL.csv')
    cerebro = bt.Cerebro()
    cerebro.adddata(feed)
    cerebro.run()
    assert len(feed) == 2
    assert feed.datetime.datetime(0) == end
