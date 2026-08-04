from services.momentum_service import MomentumService


print("🚀 Test Momentum Service 0.2")


service = MomentumService()



candle = {

    "open": 100,

    "high": 110,

    "low": 99,

    "close": 109,

    "volume": 200000,

    "money_volume": 21800000

}



result = service.analyze(

    candle,

    average_volume=100000,

    average_money_volume=10000000

)



print()

print("======================")

for key, value in result.items():

    print(
        key,
        ":",
        value
    )

print("======================")
