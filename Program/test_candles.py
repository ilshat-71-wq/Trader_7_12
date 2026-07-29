from api.bcs_api import BCSAPI


api = BCSAPI()


if api.authorize():

    candles = api.get_candles(
        "BMQ6",
        "SPBFUT"
    )


    print(candles)