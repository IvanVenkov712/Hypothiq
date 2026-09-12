from datetime import datetime, timezone

from nautilus_trader.model import Bar, BarType
from nautilus_trader.testkit.providers import TestInstrumentProvider

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model import (
    AccountType,
    BookType,
    Currency,
    Money,
    OmsType,
    Venue,
)

from buy_once import BuyOnce

instrument = TestInstrumentProvider.ethusdt_binance()

bar_type = BarType.from_str(
    "ETHUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
)

start_ns = int(
    datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
) * 1_000_000_000

bars = []
previous_close = 3000

for minute, close in enumerate([3010, 3005, 3020, 3030, 3025], start=1):
    close_ns = start_ns + minute * 60_000_000_000

    bars.append(
        Bar(
            bar_type=bar_type,
            open=instrument.make_price(previous_close),
            high=instrument.make_price(max(previous_close, close) + 5),
            low=instrument.make_price(min(previous_close, close) - 5),
            close=instrument.make_price(close),
            volume=instrument.make_qty(100),
            ts_event=close_ns,
            ts_init=close_ns,
        )
    )

    previous_close = close

engine = BacktestEngine(config=BacktestEngineConfig())

venue = Venue("BINANCE")

engine.add_venue(
    venue=venue,
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=None,
    starting_balances=[
        Money(10_000, Currency.from_str("USDT")),
    ],
    book_type=BookType.L1_MBP,
    bar_execution=True,
)

engine.add_instrument(instrument)
engine.add_data(bars)
engine.add_strategy(BuyOnce(instrument_id=instrument.id, bar_type=bar_type))

engine.run()

print(engine.generate_order_fills_report())
print(engine.generate_positions_report())
print(engine.generate_account_report(venue=venue))

engine.dispose()