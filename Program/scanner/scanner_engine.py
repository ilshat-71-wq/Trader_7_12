from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.rating_service import RatingService


class ScannerEngine:

    def __init__(self):

        self.instrument_service = InstrumentService()
        self.quote_service = QuoteService()
        self.trade_service = TradeService()
        self.rating_service = RatingService()

    # -------------------------------------------------------------

    def scan(self):

        if not self.instrument_service.connect():
            return []

        instruments = self.instrument_service.load_stocks()

        print(f"Получено инструментов: {len(instruments)}")

        rows = []

        for instrument in instruments:

            ticker = instrument.get("ticker")
            class_code = instrument.get("classCode")

            print(f"Обработка {ticker}")

            quote = self.quote_service.load(
                ticker,
                class_code
            )

            if quote is None:
                continue

            trades = self.trade_service.load(
                ticker,
                class_code
            )

            last = float(quote.get("lastPrice", 0))
            change = float(quote.get("changePercent", 0))

            volume = 0
            money_volume = 0

            records = trades.get("records", [])

            for trade in records:

                trade_volume = float(trade.get("volume", 0))
                trade_price = float(trade.get("price", 0))

                volume += trade_volume
                money_volume += trade_volume * trade_price

            rating = self.rating_service.calculate(
                last=last,
                change=change,
                volume=volume,
                money_volume=money_volume,
            )

            rows.append(
                ScannerRow(
                    ticker=ticker,
                    last=last,
                    change=change,
                    volume=volume,
                    money_volume=money_volume,
                    rating=rating,
                )
            )

        rows.sort(
            key=lambda x: (
                x.rating,
                x.money_volume,
                abs(x.change)
            ),
            reverse=True
        )

        return rows