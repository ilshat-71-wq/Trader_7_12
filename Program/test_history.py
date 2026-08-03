from services.history_service import HistoryService


service = HistoryService()


result = service.load_volume_history(

    ticker="AFLT",

    class_code="TQBR",

    interval="MINUTE_5"

)


print()

print("======================")

print(result)

print("======================")