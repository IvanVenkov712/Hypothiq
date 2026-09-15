from decimal import Decimal

import numpy as np
import pandas as pd

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.common import LogLevel
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.config import LoggerConfig
from nautilus_trader.model import AccountType, InstrumentId, BarType, Bar
from nautilus_trader.model import Currency
from nautilus_trader.model import CurrencyPair
from nautilus_trader.model import Money
from nautilus_trader.model import OmsType
from nautilus_trader.model import Price
from nautilus_trader.model import Quantity
from nautilus_trader.model import Symbol
from nautilus_trader.model import Venue

from other_simple_example import EMACross, EMACrossConfig

# Create a EUR/USD instrument on the SIM venue
EUR = Currency.from_str("EUR")
USD = Currency.from_str("USD")
EURUSD = CurrencyPair(
    instrument_id=InstrumentId.from_str("EUR/USD.SIM"),
    raw_symbol=Symbol("EUR/USD"),
    base_currency=EUR,
    quote_currency=USD,
    price_precision=5,
    size_precision=0,
    price_increment=Price.from_str("0.00001"),
    size_increment=Quantity.from_int(1),
    ts_event=0,
    ts_init=0,
    lot_size=Quantity.from_int(1_000),
    margin_init=Decimal("0.03"),
    margin_maint=Decimal("0.03"),
)

# Generate synthetic 1-minute bars (random walk around 1.10)
rng = np.random.default_rng(42)
n = 10_000
price = 1.10 + np.cumsum(rng.normal(0, 0.0002, n))
spread = np.abs(rng.normal(0, 0.0003, n))
bars_df = pd.DataFrame(
    {
        "open": price,
        "high": price + spread,
        "low": price - spread,
        "close": price + rng.normal(0, 0.00005, n),
    },
    index=pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
)
bars_df["high"] = bars_df[["open", "high", "close"]].max(axis=1)
bars_df["low"] = bars_df[["open", "low", "close"]].min(axis=1)

bar_type = BarType.from_str("EUR/USD.SIM-1-MINUTE-LAST-EXTERNAL")
bars = [
    Bar(
        bar_type=bar_type,
        open=Price(row.open, precision=EURUSD.price_precision),
        high=Price(row.high, precision=EURUSD.price_precision),
        low=Price(row.low, precision=EURUSD.price_precision),
        close=Price(row.close, precision=EURUSD.price_precision),
        volume=Quantity.from_int(1_000_000),
        ts_event=int(timestamp.value),
        ts_init=int(timestamp.value),
    )
    for timestamp, row in bars_df.iterrows()
]

engine = BacktestEngine(
    config=BacktestEngineConfig(
        logging=LoggerConfig(stdout_level=LogLevel.ERROR),
    ),
)

# Add a simulated FX venue
SIM = Venue("SIM")
engine.add_venue(
    venue=SIM,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USD)],
    base_currency=USD,
    default_leverage=Decimal(1),
)

# Add instrument, data, and strategy
engine.add_instrument(EURUSD)
engine.add_data(bars)

strategy = EMACross(
    EMACrossConfig(
        instrument_id=EURUSD.id,
        bar_type=bar_type,
        trade_size=Decimal(100000),
    ),
)
engine.add_strategy(strategy)

# Run the backtest
engine.run()


print(engine.generate_account_report(venue=SIM))
print(engine.generate_positions_report())
print(engine.generate_order_fills_report())