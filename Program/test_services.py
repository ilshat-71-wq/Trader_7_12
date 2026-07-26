from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.volume_service import VolumeService

quote = QuoteService()

if not quote.connect():
    print("Ошибка авторизации")
    exit()

trade = TradeService()

# Используем уже полученный токен
trade.api.access_token = quote.api.access_token

print("====== QUOTES ======")

q = quote.get("SBER")

print(q)

print()

print("====== LAST TRADES ======")

t = trade.get("SBER")

print(t)

print()

print("====== VOLUME ======")

volume = VolumeService.calculate(t)

print("Общий объем:", volume)