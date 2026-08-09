"""
Trader_7_12 Pro

Scanner Engine

Версия 0.3

Назначение:
- загрузка инструментов
- получение котировок
- анализ сделок
- расчет оборота
- рейтинг инструмента
- Volume Price анализ
- построение свечей
- Momentum анализ
- подготовка торгового результата
"""


from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.rating_service import RatingService
from services.candle_service import CandleService
from services.momentum_service import MomentumService

from scanner.signal_engine import SignalEngine
from scanner.trade_decision_engine import TradeDecisionEngine

from scanner.volume_price import analyze_volume



class ScannerEngine:


    def __init__(self):

        self.instrument_service = InstrumentService()

        self.quote_service = QuoteService()

        self.trade_service = TradeService()

        self.rating_service = RatingService()

        self.candle_service = CandleService()

        self.momentum_service = MomentumService()

        self.signal_engine = SignalEngine()

        self.trade_decision_engine = TradeDecisionEngine()



    # ---------------------------------------------------------

    def load(self):

        return self.scan()



    # ---------------------------------------------------------

    def scan(self):


        if not self.instrument_service.connect():

            print(
                "❌ Нет соединения BCS"
            )

            return []



        instruments = self.instrument_service.load_stocks()



        print(
            f"Получено инструментов: {len(instruments)}"
        )



        instruments = instruments[:50]



        print(
            f"Сканируем: {len(instruments)}"
        )



        rows = []



        for instrument in instruments:


            ticker = instrument.get(
                "ticker"
            )


            class_code = instrument.get(
                "classCode"
            )


            try:


                print(
                    f"Обработка {ticker}"
                )



                quote = self.quote_service.load(

                    ticker,

                    class_code

                )



                if not isinstance(
                    quote,
                    dict
                ):

                    continue



                last = float(

                    quote.get(
                        "last",
                        0
                    )

                )


                change = float(

                    quote.get(
                        "changeRate",
                        0
                    )

                )



                trades = self.trade_service.load(

                    ticker,

                    class_code

                )



                volume = 0

                money_volume = 0



                if isinstance(
                    trades,
                    dict
                ):

                    records = trades.get(

                        "records",

                        []

                    )

                else:

                    records = []



                for trade in records:


                    trade_volume = float(

                        trade.get(
                            "volume",
                            trade.get(
                                "quantity",
                                0
                            )
                        )

                    )


                    price = float(

                        trade.get(
                            "price",
                            0
                        )

                    )



                    volume += trade_volume


                    money_volume += (

                        trade_volume *

                        price

                    )



                # -----------------------------------
                # Rating
                # -----------------------------------

                rating = self.rating_service.calculate(

                    last=last,

                    change=change,

                    volume=volume,

                    money_volume=money_volume

                )


                # -----------------------------------
                # Candle + Momentum
                # -----------------------------------

                momentum = {


                    "momentum_score": 0,

                    "range_position": 0,

                    "signal": ""

                }



                candles = self.candle_service.build_candles(

                    records,

                    timeframe_minutes=5

                )


                # -----------------------------------
                # Volume baseline + market context
                # -----------------------------------

                average_volume = 0

                average_money_volume = 0

                previous_high = None

                previous_low = None


                if candles:

                    previous_candles = candles[:-1]


                    previous_volumes = [

                        c["volume"]

                        for c in previous_candles

                        if c["volume"] > 0

                    ]


                    previous_money_volumes = [

                        c["money_volume"]

                        for c in previous_candles

                        if c["money_volume"] > 0

                    ]


                    if previous_volumes:

                        average_volume = (

                            sum(previous_volumes)

                            /

                            len(previous_volumes)

                        )


                    if previous_money_volumes:

                        average_money_volume = (

                            sum(previous_money_volumes)

                            /

                            len(previous_money_volumes)

                        )


                    if previous_candles:

                        previous_high = max(

                            c["high"]

                            for c in previous_candles

                        )


                        previous_low = min(

                            c["low"]

                            for c in previous_candles

                        )


                # -----------------------------------
                # Volume Price
                # -----------------------------------

                volume_analysis = analyze_volume(

                    ticker=ticker,


                    price=last,

                    volume=volume,

                    average_volume=average_volume

                )





                if candles:


                    last_candle = candles[-1]


                    print(
                        "MOMENTUM DEBUG:",
                        ticker,
                        "candles=",
                        len(candles),
                        "avg_vol=",
                        average_volume,
                        "avg_money=",
                        average_money_volume,
                        "prev_high=",
                        previous_high,
                        "prev_low=",
                        previous_low,
                        "last_candle=",
                        last_candle
                    )


                    if ticker == "PLZL":
                        print("=== PLZL CANDLES DEBUG ===")
                        for i, c in enumerate(candles):
                            print(
                                i,
                                "time=", c.get("time"),
                                "open=", c.get("open"),
                                "high=", c.get("high"),
                                "low=", c.get("low"),
                                "close=", c.get("close"),
                                "volume=", c.get("volume"),
                                "money_volume=", c.get("money_volume")
                            )

                        print(
                            "PLZL BASELINE:",
                            "average_volume=", average_volume,
                            "average_money_volume=", average_money_volume
                        )

                    momentum = self.momentum_service.analyze(

                        last_candle,

                        average_volume=average_volume,

                        average_money_volume=average_money_volume,

                        previous_high=previous_high,

                        previous_low=previous_low

                    )


                    signal_result = self.signal_engine.analyze(

                        quote,

                        last_candle,

                        volume,

                        money_volume,

                        rating

                    )



                rows.append(

                    ScannerRow(

                        ticker=ticker,

                        lot_size=int(
                            instrument.get(
                                "lotSize",
                                1
                            )
                        ),

                        last=last,

                        change=change,

                        volume=volume,

                        money_volume=money_volume,

                        rating=rating,


                        volume_ratio=volume_analysis.get(

                            "volume_ratio",

                            0

                        ),


                        volume_score=volume_analysis.get(

                            "volume_score",

                            0

                        ),


                        momentum_score=momentum.get(

                            "momentum_score",

                            0

                        ),


                        range_position=momentum.get(

                            "range_position",

                            0

                        ),


                        signal=momentum.get(

                            "signal",

                            "NO_SIGNAL"

                        ),


                        trade_score=(

                            signal_result.get(
                                "trade_score",
                                0
                            )

                            if signal_result

                            else 0

                        ),


                        confidence=(

                            signal_result.get(
                                "confidence",
                                ""
                            )

                            if signal_result

                            else ""

                        ),


                        direction=(

                            signal_result.get(
                                "direction",
                                ""
                            )

                            if signal_result

                            else ""

                        ),


                        reasons=(

                            signal_result.get(
                                "reasons",
                                []
                            )

                            if signal_result

                            else []

                        )

                    )

                )



            except Exception as e:


                print(

                    "⚠️ Ошибка",

                    ticker,

                    e

                )

                continue



        rows = [

            r for r in rows

            if r.money_volume > 0

        ]


        rows.sort(

            key=lambda x:

            (

                x.trade_score,

                x.momentum_score,

                x.rating,

                x.money_volume

            ),

            reverse=True

        )



        # -----------------------------------
        # Trade Decision Engine
        # -----------------------------------

        trade_ideas = []


        for row in rows:

            decision = self.trade_decision_engine.evaluate(
                row
            )


            if decision.get(
                "decision"
            ) == "TRADE":

                trade_ideas.append(
                    decision
                )


        trade_ideas.sort(

            key=lambda x:

            x.get(
                "trade_score",
                0
            ),

            reverse=True

        )


        print()

        print(
            "🔥 TRADE IDEAS:"
        )


        for idea in trade_ideas[:3]:

            print()

            print(
                idea.get(
                    "ticker"
                )
            )

            print(
                "Direction:",
                idea.get(
                    "direction"
                )
            )

            print(
                "Score:",
                idea.get(
                    "trade_score"
                )
            )

            print(
                "Confidence:",
                idea.get(
                    "confidence"
                )
            )

            print(
                "Reasons:",
                idea.get(
                    "reasons"
                )
            )


        print()

        print(
            "🔥 ТОП сканера:"
        )



        for row in rows[:10]:


            print()

            print(
                row.ticker
            )

            print(
                "Цена:",
                row.last
            )

            print(
                "Оборот:",
                row.money_volume
            )

            print(
                "Rating:",
                row.rating
            )

            print(
                "Trade Score:",
                row.trade_score
            )

            print(
                "Direction:",
                row.direction
            )

            print(
                "Confidence:",
                row.confidence
            )

            print(
                "Reasons:",
                row.reasons
            )

            print(
                "Momentum:",
                row.momentum_score
            )

            print(
                "Range:",
                row.range_position
            )

            print(
                "Signal:",
                row.signal
            )



        return rows
