from services.trade_service import TradeService


service = TradeService()


data = service.load(
    "SBER",
    "TQBR"
)


print(data)