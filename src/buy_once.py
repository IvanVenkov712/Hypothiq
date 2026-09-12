from decimal import Decimal

from nautilus_trader.model import OrderSide
from nautilus_trader.trading import Strategy


class BuyOnce(Strategy):
    def __new__(cls, instrument_id, bar_type):
        # The native Strategy constructor only accepts an optional config.
        return super().__new__(cls)

    def __init__(self, instrument_id, bar_type):
        super().__init__()
        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.submitted = False

    def on_start(self):
        self.instrument = self.cache.instrument(self.instrument_id)

        if self.instrument is None:
            self.log.error("Instrument not found")
            self.stop()
            return

        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar):
        if self.submitted:
            return

        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(Decimal("0.01")),
        )

        self.submitted = True
        self.submit_order(order)

    def on_order_filled(self, event):
        self.log.info(f"Fill: {event}")

    def on_order_rejected(self, event):
        self.log.error(f"Rejected: {event}")
