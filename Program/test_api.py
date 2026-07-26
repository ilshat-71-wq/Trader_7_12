from api.bcs_api import BCSAPI

api = BCSAPI()

if api.authorize():

    print("====== QUOTES ======")

    quotes = api.get_quotes([
        {
            "ticker": "SBER",
            "classCode": "TQBR"
        }
    ])

    print(quotes)

    print()

    print("====== LAST TRADES ======")

    trades = api.get_last_trades([
        {
            "ticker": "SBER",
            "classCode": "TQBR"
        }
    ])

    print(trades)