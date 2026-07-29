from api.bcs_api import BCSAPI
from api.request_helper import RequestHelper


api = BCSAPI()


if api.authorize():

    urls = [

        "/swagger-ui.html",
        "/swagger-ui/index.html",
        "/v3/api-docs",
        "/swagger.json",
        "/openapi.json"

    ]


    for u in urls:

        url = api.market_url + u

        print("\nTEST:", url)

        r = RequestHelper.get(
            url,
            headers=api.headers()
        )

        print(
            "STATUS:",
            r.status_code
        )

        print(
            r.text[:300]
        )