import asyncio
import json
from unittest.mock import patch

import backtrader as bt
import pandas as pd
import pytest
from pydantic import ValidationError

from dto.backtest_response import BacktestResponse
from main import app
import services.registry as registry
from services.strategy_catalog import get_strategy_catalog


@pytest.fixture
def request_body():
    return {
        "strategy": {"name": "BuyAndHold"},
        "data_request": {
            "ticker": "AAPL", "start": "2024-01-01T00:00:00",
            "end": "2025-01-01T00:00:00",
        },
    }


def daily_prices(bars=8):
    return pd.DataFrame(
        {"Open": 100.0, "High": 110.0, "Low": 90.0, "Close": 100.0, "Volume": 100},
        index=pd.bdate_range("2024-01-01", periods=bars),
    )


def post_backtest(body):
    """Exercise real HTTP validation and routing without a server or HTTP client dependency."""
    messages = []

    async def receive():
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/backtests/run-backtest",
        "root_path": "", "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
    }
    asyncio.run(app(scope, receive, send))
    return messages[0]["status"], json.loads(b"".join(item.get("body", b"") for item in messages[1:]))


@pytest.mark.parametrize("overrides, field", [
    ({"interval": "1wk"}, "interval"),
    ({"interval": "1h"}, "interval"),
    ({"interval": "daily"}, "interval"),
    ({"start": "2025-01-01T00:00:00"}, "data_request"),
    ({"start": "2025-01-02T00:00:00"}, "data_request"),
    ({"start": "invalid"}, "start"),
    ({"start": "2024-01-01T00:00:00Z"}, "start"),
    ({"end": "2025-01-01T00:00:00+02:00"}, "end"),
    ({"start": "2024-01-01T12:00:00"}, "start"),
    ({"ticker": ""}, "ticker"),
    ({"ticker": " "}, "ticker"),
    ({"ticker": "AAPL MSFT"}, "ticker"),
    ({"ticker": "AAPL,MSFT"}, "ticker"),
    ({"ticker": "A" * 31}, "ticker"),
])
def test_invalid_market_requests_are_rejected_before_download(request_body, overrides, field):
    request_body["data_request"].update(overrides)
    with patch("services.market_data.yf.download") as download:
        status, payload = post_backtest(request_body)
    assert status == 422
    assert any(field in error["loc"] for error in payload["detail"])
    download.assert_not_called()


@pytest.mark.parametrize("ticker", ["BRK-B", "^GSPC", "EURUSD=X", "BTC-USD"])
def test_single_ticker_punctuation_is_preserved(request_body, ticker):
    request_body["data_request"]["ticker"] = ticker
    with patch("services.market_data.yf.download", return_value=daily_prices()) as download:
        status, _ = post_backtest(request_body)
    assert status == 200
    assert download.call_args.kwargs["tickers"] == ticker


@pytest.mark.parametrize("broker", [
    {"cash": 0}, {"cash": -1}, {"cash": "1000"}, {"cash": True},
    {"cash": float("nan")}, {"cash": float("inf")}, {"cash": -float("inf")},
    {"slippage_perc": {"perc": -0.1}}, {"slippage_perc": {"perc": 1.01}},
    {"slippage_perc": {"perc": "0.01"}}, {"slippage_perc": {"perc": float("nan")}},
    {"slippage_fixed": {"fixed": -1}}, {"slippage_fixed": {"fixed": float("inf")}},
    {"commission": {"commission": -1}}, {"commission": {"commission": float("nan")}},
    {"commission": {"commission": 1.01}},
    {"commission": {"commission": 101, "percabs": False}},
    {"commission": {"commission": 2, "commtype": 0, "margin": 100}},
    {"commission": {"leverage": 0}}, {"commission": {"leverage": float("inf")}},
    {"commission": {"mult": 0}}, {"commission": {"mult": float("nan")}},
    {"commission": {"margin": 0}}, {"commission": {"margin": -1}},
    {"commission": {"margin": float("inf")}},
    {"commission": {"interest": -1}}, {"commission": {"interest": float("nan")}},
    {"commission": {"automargin": float("inf")}},
    {"commission": {"commtype": 2}}, {"commission": {"commtype": True}},
])
def test_invalid_broker_numbers_return_serializable_field_errors(request_body, broker):
    request_body["broker"] = broker
    with patch("services.market_data.yf.download") as download:
        status, payload = post_backtest(request_body)
    assert status == 422
    assert payload["detail"][0]["loc"][:2] == ["body", "broker"]
    assert "input" not in payload["detail"][0]
    download.assert_not_called()


@pytest.mark.parametrize("commission", [
    {"commission": 2.5, "commtype": 1, "stocklike": True},
    {"commission": 2.5, "margin": 100, "mult": 10},
    {"commission": 0.1, "percabs": False},
    {"commission": 0, "automargin": -1, "margin": 100, "mult": 10},
])
def test_valid_commission_modes_keep_backtrader_semantics(request_body, commission):
    request_body["broker"] = {"commission": commission}
    with patch("services.market_data.yf.download", return_value=daily_prices()):
        status, payload = post_backtest(request_body)
    assert status == 200, payload


@pytest.mark.parametrize("name, params, field", [
    ("MACrossOver", {"fast": 0}, "fast"),
    ("MACrossOver", {"slow": -1}, "slow"),
    ("MACrossOver", {"fast": 2.5}, "fast"),
    ("MACrossOver", {"fast": True}, "fast"),
    ("MACrossOver", {"fast": "2"}, "fast"),
    ("MACrossOver", {"fast": None}, "fast"),
    ("MeanReversion", {"period": 0}, "period"),
    ("MeanReversion", {"multiplier": 0}, "multiplier"),
    ("MeanReversion", {"multiplier": float("inf")}, "multiplier"),
    ("RSIStrategy", {"lower": -1}, "lower"),
    ("RSIStrategy", {"upper": 101}, "upper"),
    ("RSIStrategy", {"upper": float("nan")}, "upper"),
    ("DonchianBreakout", {"entry_period": 0}, "entry_period"),
    ("DonchianBreakout", {"exit_period": -1}, "exit_period"),
    ("SimpleBollingerBandsBreakout", {"period": 0}, "period"),
    ("SimpleBollingerBandsBreakout", {"devfactor": -1}, "devfactor"),
    ("SimpleBollingerBandsBreakout", {"devfactor": True}, "devfactor"),
    ("BollingerBreakout", {"period": 1}, "period"),
    ("BollingerBreakout", {"stop_loss": 1}, "stop_loss"),
    ("BollingerBreakout", {"squeeze_quantile": 1.1}, "squeeze_quantile"),
    ("BollingerBreakout", {"allow_short": "false"}, "allow_short"),
    ("BollingerBreakout", {"contraction_bars": 0}, "contraction_bars"),
])
def test_invalid_strategy_values_fail_before_download(request_body, name, params, field):
    request_body["strategy"] = {"name": name, "params": params}
    with patch("services.market_data.yf.download") as download:
        status, payload = post_backtest(request_body)
    assert status == 400
    assert f"{name}.{field}:" in payload["detail"]
    download.assert_not_called()


@pytest.mark.parametrize("name, params, field", [
    ("FixedSize", {"stake": -1}, "stake"),
    ("FixedSize", {"stake": 1.5}, "stake"),
    ("FixedSize", {"stake": True}, "stake"),
    ("FixedSize", {"tranches": 0}, "tranches"),
    ("SizerFix", {"tranches": "2"}, "tranches"),
    ("FixedReverser", {"stake": float("nan")}, "stake"),
    ("FixedSizeTarget", {"tranches": -1}, "tranches"),
    ("PercentSizer", {"percents": -1}, "percents"),
    ("PercentSizer", {"percents": 101}, "percents"),
    ("PercentSizer", {"percents": float("inf")}, "percents"),
    ("PercentSizer", {"percents": True}, "percents"),
    ("PercentSizer", {"retint": 1}, "retint"),
    ("AllInSizerInt", {"percents": 101}, "percents"),
])
def test_invalid_sizing_fails_before_download(request_body, name, params, field):
    request_body["sizer"] = {"name": name, "params": params}
    with patch("services.market_data.yf.download") as download:
        status, payload = post_backtest(request_body)
    assert status == 400
    assert field in payload["detail"]
    download.assert_not_called()


@pytest.mark.parametrize("name, params, required", [
    ("MeanReversion", {"period": 3}, 3),
    ("MACrossOver", {"fast": 2, "slow": 3}, 4),
    ("MACrossOver", {"fast": 2, "slow": 3, "movav": "DEMA"}, 6),
    ("RSIStrategy", {"period": 3}, 4),
    ("DonchianBreakout", {"entry_period": 3, "exit_period": 2}, 4),
    ("SimpleBollingerBandsBreakout", {"period": 3, "devfactor": 1.5}, 3),
    ("BollingerBreakout", {"period": 3, "squeeze_lookback": 3, "stop_loss": None}, 6),
])
def test_warmup_uses_actual_bars_and_accepts_the_exact_minimum(request_body, name, params, required):
    request_body["strategy"] = {"name": name, "params": params}
    with patch("services.market_data.yf.download", return_value=daily_prices(required - 1)):
        status, payload = post_backtest(request_body)
    assert status == 400
    assert f"at least {required} daily bars" in payload["detail"]
    assert f"received {required - 1}" in payload["detail"]
    assert "earlier start date" in payload["detail"]

    with patch("services.market_data.yf.download", return_value=daily_prices(required)):
        status, payload = post_backtest(request_body)
    assert status == 200, payload
    assert len(payload["history"]) == required


def test_buy_and_hold_allows_a_single_bar_without_filling_the_pending_order(request_body):
    with patch("services.market_data.yf.download", return_value=daily_prices(1)):
        status, payload = post_backtest(request_body)
    assert status == 200
    assert len(payload["history"]) == 1
    assert payload["end_cash"] == payload["start_cash"]


@pytest.mark.parametrize("definition", get_strategy_catalog(), ids=lambda item: item.class_name)
def test_every_catalogue_default_round_trips_through_validated_execution(request_body, definition):
    request_body["strategy"] = {
        "name": definition.class_name,
        "params": {parameter.name: parameter.default for parameter in definition.parameters},
    }
    with patch("services.market_data.yf.download", return_value=daily_prices(180)):
        status, payload = post_backtest(request_body)
    assert status == 200, payload


def test_backtest_does_not_depend_on_unrelated_catalogue_entries(request_body, monkeypatch):
    class UndescribedStrategy(bt.Strategy):
        params = dict(optional=None)

    # Missing metadata for an unrelated strategy must not prevent this run.
    monkeypatch.setitem(registry._STRATEGIES, "UndescribedStrategy", UndescribedStrategy)
    with patch("services.market_data.yf.download", return_value=daily_prices()):
        status, payload = post_backtest(request_body)
    assert status == 200, payload


@pytest.mark.parametrize("name, params", [
    ("MACrossOver", {"fast": 1, "slow": 2}),
    ("RSIStrategy", {"period": 1, "lower": 0, "upper": 100}),
    ("SimpleBollingerBandsBreakout", {"period": 1, "devfactor": 0.5}),
    ("BollingerBreakout", {"period": 2, "squeeze_lookback": 2, "squeeze_quantile": 0, "stop_loss": None}),
    ("BollingerBreakout", {"period": 2, "squeeze_lookback": 2, "squeeze_quantile": 1, "allow_short": False}),
])
def test_strategy_bounds_allow_endpoints_and_fractional_numbers(request_body, name, params):
    request_body["strategy"] = {"name": name, "params": params}
    with patch("services.market_data.yf.download", return_value=daily_prices()):
        status, payload = post_backtest(request_body)
    assert status == 200, payload


@pytest.mark.parametrize("params", [
    {"percents": 0}, {"percents": 100}, {"percents": 12.5, "retint": False},
])
def test_percentage_sizing_allows_endpoints_and_fractional_numbers(request_body, params):
    request_body["sizer"] = {"name": "PercentSizer", "params": params}
    with patch("services.market_data.yf.download", return_value=daily_prices()):
        status, payload = post_backtest(request_body)
    assert status == 200, payload


@pytest.mark.parametrize("column", ["Open", "High", "Low", "Close", "Volume"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_ohlcv_is_rejected(request_body, column, value):
    frame = daily_prices().astype(float)
    frame.loc[frame.index[0], column] = value
    with patch("services.market_data.yf.download", return_value=frame):
        status, payload = post_backtest(request_body)
    assert status == 502
    assert "finite and non-missing" in payload["detail"]


@pytest.mark.parametrize("column, value, message", [
    ("Low", 0, "prices must be positive"),
    ("Low", -1, "prices must be positive"),
    ("Volume", -1, "volume nonnegative"),
    ("Open", 111, "High and Low must enclose"),
    ("Close", 111, "High and Low must enclose"),
    ("Open", 89, "High and Low must enclose"),
    ("Close", 89, "High and Low must enclose"),
    ("Low", 111, "High and Low must enclose"),
    ("High", 89, "High and Low must enclose"),
])
def test_unusable_prices_return_an_actionable_provider_error(request_body, column, value, message):
    frame = daily_prices()
    frame.loc[frame.index[0], column] = value
    with patch("services.market_data.yf.download", return_value=frame):
        status, payload = post_backtest(request_body)
    assert status == 502
    assert message in payload["detail"]
    assert "retry" in payload["detail"]


def test_valid_prices_keep_gaps_zero_volume_and_original_frame(request_body):
    frame = daily_prices().drop(index=pd.Timestamp("2024-01-03"))
    frame["Volume"] = 0
    frame["Adj Close"] = float("nan")  # Extra provider columns are not consumed by the feed.
    original = frame.copy(deep=True)
    with patch("services.market_data.yf.download", return_value=frame):
        status, payload = post_backtest(request_body)
    assert status == 200
    assert [point["time"] for point in payload["history"]] == [date.isoformat() for date in frame.index]
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("downloaded, status_code, message", [
    (None, 502, "Please retry shortly"),
    (pd.DataFrame(), 400, "Check the ticker and dates"),
])
def test_missing_downloads_have_clear_http_errors(request_body, downloaded, status_code, message):
    with patch("services.market_data.yf.download", return_value=downloaded):
        status, payload = post_backtest(request_body)
    assert status == status_code
    assert message in payload["detail"]


@pytest.mark.parametrize("failure", [TimeoutError, OSError, ValueError])
def test_download_failures_are_provider_errors_without_raw_exception_details(request_body, failure):
    with patch("services.market_data.yf.download", side_effect=failure("private provider details")):
        status, payload = post_backtest(request_body)
    assert status == 502
    assert "Could not download daily prices for AAPL" in payload["detail"]
    assert "retry" in payload["detail"]
    assert "private provider details" not in payload["detail"]


def test_exclusive_end_is_applied_before_warmup_validation(request_body):
    request_body["strategy"] = {"name": "MeanReversion", "params": {"period": 3}}
    request_body["data_request"]["end"] = "2024-01-03T00:00:00"
    with patch("services.market_data.yf.download", return_value=daily_prices(3)):
        status, payload = post_backtest(request_body)
    assert status == 400
    assert "received 2" in payload["detail"]


def test_prices_outside_the_requested_range_do_not_produce_an_empty_run(request_body):
    request_body["data_request"]["end"] = "2024-01-02T00:00:00"
    with patch("services.market_data.yf.download", return_value=daily_prices().iloc[1:]):
        status, payload = post_backtest(request_body)
    assert status == 400
    assert "No daily bars fall within" in payload["detail"]


def test_unexpected_engine_failure_is_logged_and_returns_json(request_body, caplog):
    with (
        patch("services.market_data.yf.download", return_value=daily_prices()),
        patch("backtrader.Cerebro.run", side_effect=RuntimeError("private engine details")),
    ):
        status, payload = post_backtest(request_body)
    assert status == 500
    assert "report the strategy and date range" in payload["detail"]
    assert "private engine details" not in payload["detail"]
    assert "private engine details" in caplog.text


def test_invalid_results_are_server_errors_not_request_errors(request_body):
    with pytest.raises(ValidationError) as error:
        BacktestResponse.model_validate({})
    with patch("routers.backtest_router.run_backtest_by_request", side_effect=error.value):
        status, payload = post_backtest(request_body)
    assert status == 500
    assert "invalid result" in payload["detail"]
