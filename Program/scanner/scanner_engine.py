from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.volume_service import VolumeService
from services.rating_service import RatingService


class ScannerEngine:

    def __init__(self):

        self.instrument_service = InstrumentService()
        self.quote_service = QuoteService()
        self.trade_service = TradeService()

    # ---------------------------------------------------------

    def scan(self):

        rows = []

        #
        # Авторизация
        #
        if not self.instrument_service.connect():
            return rows

        #
        # Загружаем акции
        #
        instruments = self.instrument_service.load_stocks()

        if not instruments:
            return rows

        print(f"Получено инструментов: {len(instruments)}")

        #
        # Обрабатываем все бумаги
        #
        for instrument in instruments:

            ticker = instrument["ticker"]
            class_code = instrument["classCode"]

            print(f"Обработка {ticker}")

            #
            # Котировки
            #
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

            #
            # Сделки
            #
            trades = self.trade_service.load(
                ticker,
                class_code
            )

            #
            # Объемы
            #
            volume, money = VolumeService.calc(
                q["last"],
                trades
            )

            #
            # Новый рейтинг
            #
            rating = RatingService.calc(
                change=q["changeRate"],
                money_volume=money,
                volume=volume
            )

            #
            # Строка таблицы
            #
            row = ScannerRow(
                ticker=ticker,
                last=q["last"],
                change=q["changeRate"],
                volume=volume,
                money_volume=money,
                rating=rating
            )

            rows.append(row)

        #
        # Сортировка теперь по рейтингу
        #
        rows.sort(
            key=lambda x: x.rating,
            reverse=True
        )

        return rows