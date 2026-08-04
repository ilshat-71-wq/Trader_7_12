from scanner.signal_engine import SignalEngine


print("🚀 Test Signal Engine 0.3")


engine = SignalEngine()



quote = {

    "ticker": "SBER",

    "last": 282.5,

    "changeRate": 2.8,

    "bid": 282.45,

    "offer": 282.50,

    "volume_score": 80

}



momentum = {

    "momentum_score": 81,

    "volume_ratio": 2.16,

    "money_volume_ratio": 1.9,

    "breakout_strength": 100,

    "true_breakout": True,

    "signal": "STRONG_LONG"

}



result = engine.analyze(

    quote,

    momentum

)



print()

print("======================")

for key, value in result.items():

    print(
        key,
        ":",
        value
    )

print("======================")
