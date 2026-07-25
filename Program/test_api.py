from api.bcs_api import BCSAPI

api = BCSAPI()

if api.authorize():

    print("Получаем список акций...")

    data = api.get_instruments("STOCK")

    if data is None:
        print("Ошибка получения данных")

    else:
        print(type(data))

        try:
            print("Количество объектов:", len(data))
        except:
            print("Не удалось определить количество")

        print("Первые данные:")

        print(data[0])