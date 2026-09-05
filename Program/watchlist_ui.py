"""Trader_7_12 Pro — final dashboard wrapper."""

from ui import TraderWindow


class WatchlistTraderWindow(TraderWindow):
    """Canonical read-only market-information dashboard entry point.

    All scanner execution and rendering live in TraderWindow. The application
    reports market facts and relative strength/weakness; it does not label
    results as trade candidates or make trading decisions.
    """

    VERSION = "2.3.1"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.subtitle.setText("D1 • ЛИДЕРЫ / АУТСАЙДЕРЫ • MONEY FLOW • RS • READ-ONLY")
