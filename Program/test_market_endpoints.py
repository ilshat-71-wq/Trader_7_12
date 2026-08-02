from api.bcs_api import BCSAPI
from api.request_helper import RequestHelper


api = BCSAPI()

api.authorize()


endpoints = [
    "/last-trades",
    "/trades",
    "/executions",
    "/deals",
    "/statistics",
    "/market-statistics",
    "/volume",
    "/summary"
]


for ep in endpoints:

    url = api.market_url + ep

    print()
    print("TEST:", ep)

    r = RequestHelper.post(
        url,
        headers={
            **api.headers(),
            "Content-Type": "application/json"
        },
        json={
            "ticker": "SBER",
            "classCode": "TQBR"
        }
    )

    print("STATUS:", r.status_code)
    print(r.text[:200])
