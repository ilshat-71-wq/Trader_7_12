"""
Trader_7_12 Pro

Test Candle Loader Service
"""


from services.candle_loader_service import CandleLoaderService



print("🚀 Test Candle Loader Service")


service = CandleLoaderService()


candles = service.load(

    ticker="SBER",

    class_code="TQBR",

    timeframe_minutes=5

)


print()

print("======================")

print(
    "Свечей получено:",
    len(candles)
)


for candle in candles[:10]:

    print()

    print(candle)


print()

print("======================")