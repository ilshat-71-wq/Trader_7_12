from services.candle_service import CandleService


print("🚀 Test Candle Service")


trades = [

    {
        "price": 100,
        "volume": 10,
        "time": "2026-08-03T10:01:10Z"
    },

    {
        "price": 102,
        "volume": 20,
        "time": "2026-08-03T10:03:30Z"
    },

    {
        "price": 98,
        "volume": 15,
        "time": "2026-08-03T10:04:50Z"
    },

    {
        "price": 105,
        "volume": 30,
        "time": "2026-08-03T10:06:10Z"
    },

]


service = CandleService()


candles = service.build_candles(
    trades,
    timeframe_minutes=5
)


print()

print("======================")

for candle in candles:

    print(candle)

print("======================")