from api.bcs_api import BCSAPI


api = BCSAPI()

api.authorize()

data = api.get_candles(
    "SBER",
    "TQBR"
)

print()
print("========== RAW CANDLES ==========")
print(data)
print("=================================")
