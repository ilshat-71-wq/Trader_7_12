from datetime import datetime

from api.bcs_api import BCSAPI


class TradeService:


    def __init__(self):

        self.api = BCSAPI()

        self.api.authorize()



    # ---------------------------------------------------------

    def load(
        self,
        ticker,
        class_code
    ):


        print()

        print(
            f"TradeService: {ticker} {class_code}"
        )


        result = self.api.get_last_trades(

            ticker,

            class_code

        )


        print()

        print("========== RAW TRADES ==========")

        print(result)

        print("================================")



        return result



    # ---------------------------------------------------------

    def load_history(
        self,
        ticker,
        class_code,
        start_time,
        end_time
    ):


        print()

        print(
            f"TradeService HISTORY: {ticker} {class_code}"
        )


        def normalize_time(value):

            if isinstance(value, datetime):
                return value.isoformat()

            return str(value)


        start_time = normalize_time(start_time)
        end_time = normalize_time(end_time)


        payload = {


            "ticker":

                ticker,


            "classCode":

                class_code,


            "startDateTime":

                start_time,


            "endDateTime":

                end_time

        }



        print()

        print(
            "HISTORY TRADE PAYLOAD:"
        )

        print(payload)



        result = self.api.get_trades_period(

            ticker,

            class_code,

            start_time,

            end_time

        )



        print()

        print(
            "========== RAW HISTORY TRADES =========="
        )

        print(result)

        print(
            "========================================"
        )



        return result
