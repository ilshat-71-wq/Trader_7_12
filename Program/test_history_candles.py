from services.live_trade_collector import LiveTradeCollector
from services.candle_service import CandleService


collector = LiveTradeCollector()

candle_service = CandleService()


trades = collector.load(
    "SBER",
    "TQBR",
    "2026-08-03T20:00:00.000Z",
    "2026-08-03T20:50:00.000Z"
)


print()

print(
    "TOTAL TRADES:",
    len(trades)
)


candles = candle_service.build_candles(
    trades,
    5
)


print()

print(
    "TOTAL CANDLES:",
    len(candles)
)


for candle in candles:

    print()

    print(candle)
