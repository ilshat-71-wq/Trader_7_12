from services.live_trade_collector import LiveTradeCollector
from services.candle_service import CandleService
from services.momentum_service import MomentumService

from datetime import datetime, timedelta, timezone



print("🚀 Test History Momentum 0.3")



ticker = "SBER"
class_code = "TQBR"



collector = LiveTradeCollector()

candle_service = CandleService()

momentum_service = MomentumService()



end_time = datetime.now(
    timezone.utc
)

start_time = end_time - timedelta(
    minutes=60
)



trades = collector.load(
    ticker,
    class_code,
    start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    end_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
)



print()

print(
    "TOTAL TRADES:",
    len(trades)
)



candles = candle_service.build_candles(
    trades,
    timeframe_minutes=5
)



print()

print(
    "TOTAL CANDLES:",
    len(candles)
)



if not candles:
    exit()



average_volume = sum(
    c["volume"]
    for c in candles
) / len(candles)



average_money_volume = sum(
    c["money_volume"]
    for c in candles
) / len(candles)



print()

print("==============================")
print("MOMENTUM REPORT 0.3")
print("==============================")



previous_high = None

previous_low = None



for candle in candles:


    result = momentum_service.analyze(

        candle,

        average_volume,

        average_money_volume,

        previous_high,

        previous_low

    )



    print()

    print(
        candle["time"]
    )

    print(
        "Close:",
        candle["close"]
    )

    print(
        "Prev High:",
        previous_high
    )

    print(
        "Prev Low:",
        previous_low
    )

    print(
        "Momentum:",
        result["momentum_score"]
    )

    print(
        "Volume Ratio:",
        result["volume_ratio"]
    )

    print(
        "Breakout:",
        result["breakout_strength"]
    )

    print(
        "True:",
        result["true_breakout"]
    )

    print(
        "SIGNAL:",
        result["signal"]
    )



    previous_high = candle["high"]

    previous_low = candle["low"]

