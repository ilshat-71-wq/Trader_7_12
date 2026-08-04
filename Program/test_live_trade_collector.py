from services.live_trade_collector import LiveTradeCollector


collector = LiveTradeCollector()


trades = collector.load(
    "SBER",
    "TQBR",
    "2026-08-03T20:00:00.000Z",
    "2026-08-03T20:50:00.000Z"
)


print()

print(
    "TRADES:",
    len(trades)
)


for trade in trades[:5]:

    print(trade)
