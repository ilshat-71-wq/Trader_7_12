from api.bcs_api import BCSAPI


api = BCSAPI()

api.authorize()

data = api.get_quotes(
    [
        {
            "ticker": "SBER",
            "classCode": "TQBR"
        }
    ]
)

print()
print("========== RAW QUOTE SBER ==========")
print(data)
print("====================================")
