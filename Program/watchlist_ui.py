"""Trader_7_12 Pro — final dashboard wrapper."""

from ui import TraderWindow
from services.market_information_scanner_service import MarketInformationScannerService


class WatchlistTraderWindow(TraderWindow):
    """Canonical read-only market-information dashboard entry point.

    The runtime scanner exposed to the UI is the informational facade: market
    leaders, market laggards and current attention only. No trading decision
    is presented by the application.
    """

    VERSION = "2.3.1"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        if scanner_enabled:
            self.scanner = MarketInformationScannerService()
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.subtitle.setText("D1 • ЛИДЕРЫ / АУТСАЙДЕРЫ • MONEY FLOW • RS • READ-ONLY")
