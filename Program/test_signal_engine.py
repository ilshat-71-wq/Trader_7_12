from scanner.signal_engine import SignalEngine


quotes = [

    {
        "ticker": "BMQ6",
        "last": 83.95,
        "changeRate": -6.59,
        "bid": 83.67,
        "offer": 84.25
    },

    {
        "ticker": "GDU6",
        "last": 4044.5,
        "changeRate": -1.30,
        "bid": 4044,
        "offer": 4050
    }

]


engine = SignalEngine()


engine.rank(
    quotes
)


engine.print_report()