from api.bcs_api import BCSAPI

api = BCSAPI()

if api.authorize():

    quotes = api.get_quotes([
        {
            "ticker": "SBER",
            "classCode": "TQBR"
        }
    ])

    print(quotes)