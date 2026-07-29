"""
Trader_7_12 Pro
Module: Volume x Price Analyzer

Назначение:
- расчет денежного оборота инструмента
- оценка всплеска объема
- подготовка рейтинга для сканера MOEX Futures

Версия: 0.3
"""


def calculate_volume_price(volume: int, price: float) -> float:
    """
    Расчет объема в деньгах

    volume - количество контрактов
    price  - цена инструмента

    пример:
    100000 контрактов * 34500 руб.
    = 3 450 000 000 руб.
    """

    return volume * price



def volume_ratio(current_volume: int, average_volume: int) -> float:
    """
    Во сколько раз текущий объем выше среднего
    """

    if average_volume == 0:
        return 0

    return round(
        current_volume / average_volume,
        2
    )



def volume_score(current_volume: int,
                 average_volume: int) -> int:
    """
    Оценка силы объема 0-100

    >3x среднего = сильный импульс
    >2x = хороший
    >1.5x = внимание
    """

    ratio = volume_ratio(
        current_volume,
        average_volume
    )


    if ratio >= 3:
        return 100

    elif ratio >= 2:
        return 80

    elif ratio >= 1.5:
        return 60

    elif ratio >= 1:
        return 40

    else:
        return 20



def analyze_volume(
        ticker: str,
        price: float,
        volume: int,
        average_volume: int
):
    """
    Полный анализ инструмента
    """

    money_volume = calculate_volume_price(
        volume,
        price
    )

    ratio = volume_ratio(
        volume,
        average_volume
    )

    score = volume_score(
        volume,
        average_volume
    )


    return {

        "ticker": ticker,

        "price": price,

        "volume": volume,

        "money_volume": money_volume,

        "volume_ratio": ratio,

        "volume_score": score

    }



# Тестовый запуск
if __name__ == "__main__":


    result = analyze_volume(
        ticker="SBER-9.26",
        price=34500,
        volume=150000,
        average_volume=60000
    )


    for key, value in result.items():

        print(
            f"{key}: {value}"
        )