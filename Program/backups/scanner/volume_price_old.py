"""
Trader_7_12 Pro

Module: Volume x Price Analyzer

Версия: 0.4

Назначение:
- расчет денежного оборота
- анализ силы объема
- анализ движения цены
- определение положения цены в диапазоне
- подготовка данных для Signal Engine
"""


# ---------------------------------------------------------
# Денежный оборот
# ---------------------------------------------------------

def calculate_volume_price(
        volume: int,
        price: float
) -> float:
    """
    Денежный оборот инструмента
    """

    return volume * price



# ---------------------------------------------------------
# Соотношение текущего объема к среднему
# ---------------------------------------------------------

def volume_ratio(
        current_volume: int,
        average_volume: int
) -> float:
    """
    Во сколько раз текущий объем выше среднего
    """

    if average_volume == 0:
        return 0


    return round(
        current_volume / average_volume,
        2
    )



# ---------------------------------------------------------
# Оценка объема
# ---------------------------------------------------------

def volume_score(
        current_volume: int,
        average_volume: int
) -> int:
    """
    Оценка силы объема 0-100
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



# ---------------------------------------------------------
# Движение цены
# ---------------------------------------------------------

def price_momentum_score(
        change_percent: float
) -> int:
    """
    Оценка движения цены

    максимум 100
    """


    change = abs(change_percent)


    if change >= 5:
        return 100

    elif change >= 3:
        return 80

    elif change >= 2:
        return 60

    elif change >= 1:
        return 40

    elif change >= 0.5:
        return 20

    return 0



# ---------------------------------------------------------
# Позиция цены в диапазоне
# ---------------------------------------------------------

def range_position(
        price: float,
        low: float,
        high: float
) -> float:
    """
    Где находится цена внутри диапазона.

    0.0 = минимум
    1.0 = максимум
    """


    if high <= low:
        return 0


    position = (

        (price - low)

        /

        (high - low)

    )


    return round(
        position,
        2
    )



# ---------------------------------------------------------
# Итоговый сигнал
# ---------------------------------------------------------

def breakout_signal(
        position: float,
        volume_ratio_value: float,
        change_percent: float
) -> str:
    """
    Простая оценка пробоя
    """


    if (

        position >= 0.85

        and volume_ratio_value >= 2

        and change_percent > 0

    ):

        return "BREAKOUT_WATCH"


    if (

        position <= 0.15

        and volume_ratio_value >= 2

        and change_percent < 0

    ):

        return "BREAKDOWN_WATCH"


    return "NO_SIGNAL"



# ---------------------------------------------------------
# Полный анализ
# ---------------------------------------------------------

def analyze_volume(
        ticker: str,
        price: float,
        volume: int,
        average_volume: int,
        change_percent: float = 0,
        low: float = 0,
        high: float = 0
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


    v_score = volume_score(
        volume,
        average_volume
    )


    momentum = price_momentum_score(
        change_percent
    )


    position = range_position(
        price,
        low,
        high
    )


    signal = breakout_signal(
        position,
        ratio,
        change_percent
    )


    return {


        "ticker": ticker,


        "price": price,


        "volume": volume,


        "money_volume": money_volume,


        "volume_ratio": ratio,


        "volume_score": v_score,


        "momentum_score": momentum,


        "range_position": position,


        "signal": signal

    }



# ---------------------------------------------------------
# Тест
# ---------------------------------------------------------

if __name__ == "__main__":


    result = analyze_volume(

        ticker="AFLT",

        price=35.22,

        volume=23_000_000,

        average_volume=8_000_000,

        change_percent=3.2,

        low=33.5,

        high=35.5

    )


    for key, value in result.items():

        print(
            f"{key}: {value}"
        )