from api.bcs_api import BCSAPI
from api.request_helper import RequestHelper


api = BCSAPI()


if api.authorize():

    urls = [

        "/order-book",
        "/orderbook",
        "/market-depth",
        "/depth",
        "/orderbook-level2"

    ]


    for endpoint in urls:

        url = api.market_url + endpoint


        print("\nTEST:", endpoint)


        r = RequestHelper.post(

            url,

            headers={

                **api.headers(),

                "Content-Type": "application/json"

            },

            json={

                "ticker": "BMQ6",

                "classCode": "SPBFUT",

                "depth": 10

            }

        )


        print(
            "STATUS:",
            r.status_code
        )


        print(
            r.text[:200]
        )