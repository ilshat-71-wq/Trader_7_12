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

    @staticmethod
    def _serialize_datetime(value):
        """Convert datetime-like values to BCS-compatible ISO strings."""
        if hasattr(value, "isoformat"):
            text = value.isoformat()
        else:
            text = str(value).strip()

        if text.endswith("+00:00"):
            return text[:-6] + "Z"

        if text.endswith("Z"):
            return text

        return text


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


        start_time = self._serialize_datetime(start_time)
        end_time = self._serialize_datetime(end_time)

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
