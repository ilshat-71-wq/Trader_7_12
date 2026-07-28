from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.volume_service import VolumeService


class ScannerEngine:

    def __init__(self):

        self.instrument_service = InstrumentService()
        self.quote_service = QuoteService()
        self.trade_service = TradeService()

    def scan(self):

        rows = []

        if not self.instrument_service.connect():
            return rows

        instruments = self.instrument_service.load_stocks()

        print(f"Получено инструментов: {len(instruments)}")

        for instrument in instruments[:50]:

            ticker = instrument["ticker"]

            #
            # Для акций всегда используем TQBR
            #
            class_code = "TQBR"

            print(f"Обработка {ticker}")

            quote = self.quote_service.load(
                ticker,
                class_code
            )

            if not quote:
                continue

            records = quote.get("records", [])

            if len(records) == 0:
                continue

            q = records[0]

            trades = self.trade_service.load(
                ticker,
                class_code
            )

            volume, money = VolumeService.calc(
                q["last"],
                trades
            )

            rows.append(
                ScannerRow(
                    ticker=ticker,
                    last=q["last"],
                    change=q["changeRate"],
                    volume=volume,
                    money_volume=money,
                    rating=0
                )
            )

        rows.sort(
            key=lambda x: x.money_volume,
            reverse=True
        )

        return rows