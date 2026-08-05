"""
Trader_7_12 Pro

Volume Scanner

Версия 0.5

Назначение:
- расчёт ликвидности инструментов
- денежный оборот
- сила объёма
- импульс цены
- подготовка данных для Signal Engine
"""


from scanner.instrument_loader import InstrumentLoader
from scanner.volume_price import analyze_volume
from api.bcs_api import BCSAPI

from services.candle_service import CandleService
from services.momentum_service import MomentumService
from services.volume_score_service import VolumeScoreService
from services.trade_score_service import TradeScoreService
from services.diagnostic_service import DiagnosticService
from services.breakout_service import BreakoutService
from services.breakout_quality_service import BreakoutQualityService
from services.trade_plan_service import TradePlanService
from services.trade_filter_service import TradeFilterService
from services.trade_idea_service import TradeIdeaService
from services.signal_engine import SignalEngine



class VolumeScanner:


    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()

        self.candle_service = CandleService()

        self.momentum_service = MomentumService()

        self.trade_score_service = TradeScoreService()
        self.diagnostic_service = DiagnosticService()
        self.volume_score_service = VolumeScoreService()
        self.breakout_service = BreakoutService()
        self.breakout_quality_service = BreakoutQualityService()
        self.trade_plan_service = TradePlanService()
        self.trade_filter_service = TradeFilterService()
        self.trade_idea_service = TradeIdeaService()
        self.signal_engine = SignalEngine()



    def start(self):

        print(
            "📊 Volume Scanner v0.5"
        )


        instruments = self.loader.load()


        if not instruments:

            print(
                "❌ Нет инструментов"
            )

            return []



        if not self.api.authorize():

            print(
                "❌ Ошибка авторизации"
            )

            return []



        result = []



        for item in instruments[:50]:


            ticker = item.get(
                "ticker"
            )


            class_code = item.get(
                "classCode"
            )



            trades = self.api.get_last_trades(

                ticker,

                class_code

            )



            records = trades.get(
                "records",
                []
            )



            if not records:

                continue



            total_volume = 0

            money_volume = 0

            prices = []



            for trade in records:


                price = float(

                    trade.get("price", 0)

                )


                volume = float(

                    trade.get("volume", 0)

                )


                total_volume += volume


                money_volume += (

                    price *

                    volume

                )


                prices.append(price)



            if not prices:

                continue


            candles = self.candle_service.build_candles(
                records,
                timeframe_minutes=5
            )

            print("DEBUG candles:", len(candles))


            average_volume = total_volume / 5
            average_money_volume = 0
            previous_high = None
            previous_low = None



            if candles:

                previous_candles = candles[:-1]

                print("DEBUG previous candles:")
                for c in previous_candles:
                    print(c)

                if previous_candles:

                    vols = [c["volume"] for c in previous_candles if c["volume"] > 0]
                    money = [c["money_volume"] for c in previous_candles if c["money_volume"] > 0]

                    if vols:
                        average_volume = sum(vols) / len(vols)

                    if money:
                        average_money_volume = sum(money) / len(money)

                    previous_high = max(c["high"] for c in previous_candles)
                    previous_low = min(c["low"] for c in previous_candles)

            current_price = prices[0]


            low = min(prices)

            high = max(prices)



            change_percent = (

                (current_price - low)

                /

                low

                *

                100

            ) if low else 0



            analysis = analyze_volume(

                ticker=ticker,

                price=current_price,

                volume=int(total_volume),

                average_volume=average_volume,

                change_percent=change_percent,

                low=low,

                high=high

            )




            if candles:

                momentum = self.momentum_service.analyze(

                    candles[-1],

                    average_volume=average_volume,

                    average_money_volume=average_money_volume,

                    previous_high=previous_high,

                    previous_low=previous_low

                )

                analysis["momentum_score"] = momentum["momentum_score"]

                analysis["momentum_signal"] = momentum["signal"]



            analysis["trades"] = len(records)

            analysis["classCode"] = class_code

            analysis["money_volume_real"] = money_volume


            volume_score = self.volume_score_service.calculate(

                volume=int(total_volume),

                average_volume=average_volume,

                money_volume=money_volume,

                average_money_volume=average_money_volume

            )


            analysis.update(volume_score)


            breakout = self.breakout_service.analyze(

                current_price=current_price,

                previous_high=previous_high,

                previous_low=previous_low,

                volume_ratio=volume_score["volume_ratio"]

            )


            analysis.update(breakout)

            current_candle = candles[-1]

            breakout_quality = self.breakout_quality_service.analyze(

                current_price=current_price,

                open_price=current_candle["open"],

                high_price=current_candle["high"],

                low_price=current_candle["low"],

                close_price=current_candle["close"],

                previous_high=previous_high,

                previous_low=previous_low

            )

            analysis.update(breakout_quality)
            analysis["current_price"] = current_price



            result.append(

                analysis

            )



        # ---------------------------------------------------------
        # Итоговый торговый рейтинг
        # ---------------------------------------------------------

        for item in result:

            item["trade_score"] = self.trade_score_service.calculate(

                volume_score=item.get("volume_score", 0),

                momentum_score=item.get("momentum_score", 0),

                signal=item.get("momentum_signal", "NO_SIGNAL"),

                breakout_score=item.get(
                    "breakout_score",
                    0
                )

            )



            signal_result = self.signal_engine.analyze(item)

            item["final_signal"] = signal_result["signal"]

            item["confidence"] = signal_result["confidence"]

            item["reasons"] = signal_result["reasons"]


            trade_plan = self.trade_plan_service.generate_plan(

                current_price=item["current_price"],

                signal=signal_result["signal"],

                momentum_score=item.get(
                    "momentum_score",
                    0
                ),

                breakout_score=item.get(
                    "breakout_score",
                    0
                )

            )


            item.update(trade_plan)


            filter_result = self.trade_filter_service.check(

                signal=signal_result["signal"],

                confidence=signal_result["confidence"],

                breakout_score=item.get(
                    "breakout_score",
                    0
                ),

                trade_score=item.get(
                    "trade_score",
                    {}
                ).get(
                    "trade_score",
                    0
                ),

                rr_ratio=item.get(
                    "rr_ratio",
                    0
                )

            )


            item["trade_allowed"] = filter_result["allowed"]

            item["trade_filter_level"] = filter_result.get(
                "level"
            )

            item["trade_filter_reason"] = filter_result["reason"]


            trade_idea = self.trade_idea_service.generate(item)

            item["trade_idea"] = trade_idea

        result.sort(

            key=lambda x:

            (
                x.get("trade_score", {}).get("score", 0)
                if isinstance(
                    x.get("trade_score"),
                    dict
                )
                else x.get("trade_score", 0)
            ),

            reverse=True

        )



        print()

        print(
            "🔥 TOP LIQUIDITY"
        )


        for item in result[:10]:

            self.diagnostic_service.print_analysis(item)

            print(

                item["ticker"],

                "оборот:",

                round(

                    item["money_volume"],

                    2

                ),

                "volume:",

                item["volume_score"],

                "momentum:",

                item["momentum_score"],

                "TRADE SCORE:",

                item["trade_score"],

                "signal:",

                item["final_signal"],

                "ENTRY:", item.get("entry"),

                "STOP:", item.get("stop_loss"),

                "TARGET:", item.get("take_profit"),

                "RR:", item.get("rr_ratio")

            )



        return result





if __name__ == "__main__":

    scanner = VolumeScanner()

    scanner.start()

