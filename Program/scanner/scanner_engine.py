from services.instrument_service import InstrumentService
from models.scanner_row import ScannerRow


class ScannerEngine:

    def __init__(self):

        self.instrument_service = InstrumentService()

    def load(self):

        if not self.instrument_service.connect():
            return []

        stocks = self.instrument_service.load_stocks()

        result = []

        for item in stocks:

            row = ScannerRow(

                ticker=item.get("ticker"),

                short_name=item.get("shortName"),

                sector=item.get("businessSector"),

                short_allowed=item.get("isCanShort"),

                margin_allowed=item.get("isCanMargin"),

                market_cap=item.get("mktcap", 0)

            )

            result.append(row)

        return result