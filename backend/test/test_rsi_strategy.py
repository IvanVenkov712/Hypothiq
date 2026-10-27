import backtrader as bt
import pandas as pd
import pytest

from precoded_strategies.single_asset import RSIStrategy


@pytest.mark.parametrize('runonce', [True, False])
@pytest.mark.parametrize('prices, expected_rsi, expected_position', [
    pytest.param([100] * 30, 50, 0, id='flat'),
    pytest.param(list(range(100, 130)), 100, 0, id='rising'),
    pytest.param(list(range(130, 100, -1)), 0, 1, id='falling'),
])
def test_rsi_handles_prices_with_no_gains_or_losses(
    runonce, prices, expected_rsi, expected_position,
):
    frame = pd.DataFrame(
        {'open': prices, 'high': prices, 'low': prices, 'close': prices, 'volume': 100},
        index=pd.date_range('2024-01-01', periods=len(prices)),
    )
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=frame))
    cerebro.addstrategy(RSIStrategy)

    strategy = cerebro.run(runonce=runonce)[0]

    assert strategy.rsi[0] == pytest.approx(expected_rsi)
    assert strategy.position.size == expected_position
