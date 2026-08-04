from scanner.signal_engine import SignalEngine


engine = SignalEngine()


quotes = [

    {
        "ticker": "SBER",
        "last": 281.40,
        "changeRate": 2.5,
        "bid": 281.35,
        "offer": 281.45
    },

    {
        "ticker": "LKOH",
        "last": 7200,
        "changeRate": -1.8,
        "bid": 7198,
        "offer": 7202
    }

]


result = engine.rank(quotes)


print()

print("RESULT:")

for x in result:

    print()

    print(x)

