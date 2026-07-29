from api.bcs_api import BCSAPI


api = BCSAPI()


if api.authorize():

    print()
    print("====== QUOTES ======")

    quotes = api.get_quotes(
        [
            {
                "ticker": "SBER",
                "classCode": "TQBR"
            }
        ]
    )

    print(quotes)


    print()
    print("====== LAST TRADES ======")

    trades = api.get_last_trades(
        "SBER",
        "TQBR"
    )

    print(trades)