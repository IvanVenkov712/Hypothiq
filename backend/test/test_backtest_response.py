import json

import pytest
from pydantic import ValidationError

from dto.backtest_response import BacktestHistoryPoint


@pytest.fixture
def history_point():
    return {
        'time': '2024-01-04T00:00:00',
        'close': 90,
        'cash': 800,
        'equity': 980,
        'drawdown': 2,
    }


def test_history_point_serializes_bar_label_and_numeric_values(history_point):
    point = BacktestHistoryPoint.model_validate(history_point)

    assert point.time.tzinfo is None
    assert json.loads(point.model_dump_json()) == history_point


@pytest.mark.parametrize('field', ['close', 'cash', 'equity', 'drawdown'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_history_rejects_nonfinite_chart_values(history_point, field, value):
    with pytest.raises(ValidationError) as error:
        BacktestHistoryPoint.model_validate({**history_point, field: value})

    assert error.value.errors()[0]['loc'] == (field,)


@pytest.mark.parametrize('overrides', [
    {'time': 'not-a-date'},
    {'time': '2024-01-04T00:00:00Z'},
    {'drawdown': -1},
])
def test_history_rejects_invalid_bar_labels_and_negative_drawdown(history_point, overrides):
    with pytest.raises(ValidationError):
        BacktestHistoryPoint.model_validate({**history_point, **overrides})


def test_history_requires_close(history_point):
    del history_point['close']

    with pytest.raises(ValidationError) as error:
        BacktestHistoryPoint.model_validate(history_point)

    assert error.value.errors()[0]['loc'] == ('close',)
