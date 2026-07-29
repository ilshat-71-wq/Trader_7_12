from api.bcs_api import BCSAPI


api = BCSAPI()


if api.authorize():

    book = api.get_order_book(
        "BMQ6",
        "SPBFUT"
    )

    print(book)