"""Trader_7_12 Pro — final dashboard wrapper."""

from ui import TraderWindow


class WatchlistTraderWindow(TraderWindow):
    """Compatibility entry point for the desktop launcher.

    All scanner execution and rendering now live in the canonical TraderWindow.
    No legacy setup/radar pipeline is retained here.
    """

    VERSION = "2.3.0"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — Market Attention Radar")
        self.subtitle.setText("D1 • MARKET ATTENTION • MONEY FLOW • RS • READ-ONLY")
