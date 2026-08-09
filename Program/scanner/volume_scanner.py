"""
Trader_7_12 Pro

Volume Scanner

Версия 0.8

Назначение:

- расчёт ликвидности инструментов
- денежный оборот
- сила объёма
- импульс цены
- Relative Strength относительно IMOEX
- breakout
- торговый рейтинг
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
from services.trade_confirmation_service import TradeConfirmationService
from services.trade_idea_service import TradeIdeaService
from services.signal_engine import SignalEngine
from services.trade_ranker_service import TradeRankerService
from services.portfolio_manager_service import PortfolioManagerService
from services.trade_journal_service import TradeJournalService
from services.trade_outcome_service import TradeOutcomeService
from services.outcome_manager_service import OutcomeManagerService
from services.relative_strength_service import RelativeStrengthService


class VolumeScanner:

    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()

        self.candle_service = CandleService()

        self.relative_strength_service = RelativeStrengthService()

        self.momentum_service = MomentumService()

        self.trade_score_service = TradeScoreService()
        self.diagnostic_service = DiagnosticService()
        self.volume_score_service = VolumeScoreService()
        self.breakout_service = BreakoutService()
        self.breakout_quality_service = BreakoutQualityService()
        self.trade_plan_service = TradePlanService()
        self.trade_filter_service = TradeFilterService()
        self.trade_confirmation_service = TradeConfirmationService()
        self.trade_idea_service = TradeIdeaService()
        self.signal_engine = SignalEngine()
        self.trade_ranker_service = TradeRankerService()
        self.portfolio_manager_service = PortfolioManagerService()
        self.trade_journal_service = TradeJournalService()

        self.trade_outcome_service = TradeOutcomeService()

        self.outcome_manager_service = OutcomeManagerService(
            self.trade_journal_service,
            self.trade_outcome_service
        )

    def start(self):
        """
        Compatibility wrapper для старого CLI-запуска.
        """
        return self.scan()

    def scan(self, instruments=None):
        """
        Основной публичный метод VolumeScanner.

        Если instruments переданы извне — используем их.
        Если нет — загружаем самостоятельно.
        """

        print(
            "📊 Volume Scanner v0.8"
        )

        if instruments is None:
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

        # ---------------------------------------------------------
        # RAW MARKET DATA
        # ---------------------------------------------------------
        #
        # ВАЖНО:
        # Каждый инструмент запрашивается только один раз.
        #
        # Это особенно важно для MX benchmark.
        #
        # Раньше MMU6 запрашивался отдельно до основного цикла,
        # а затем повторно внутри цикла. Два запроса могли вернуть
        # разное количество сделок.
        #
        # Теперь сначала собираем данные всех инструментов,
        # включая MX, и только после этого рассчитываем RS.
        # ---------------------------------------------------------

        market_data = {}

        print()
        print(
            "================ MARKET DATA COLLECTION ================"
        )

        for item in instruments[:50]:

            ticker = item.get(
                "ticker"
            )

            class_code = item.get(
                "classCode"
            )

            if not ticker or not class_code:
                continue

            trades = self.api.get_last_trades(
                ticker,
                class_code
            )

            records = trades.get(
                "records",
                []
            )

            print(
                "MARKET DATA:",
                ticker,
                "trades:",
                len(records)
            )

            if not records:
                continue

            candles = self.candle_service.build_candles(
                records,
                timeframe_minutes=5
            )

            market_data[ticker] = {
                "item": item,
                "records": records,
                "candles": candles
            }

        # ---------------------------------------------------------
        # RELATIVE STRENGTH BENCHMARK
        # ---------------------------------------------------------
        #
        # Benchmark = ближайший IMOEX futures.
        #
        # IMOEXF является фьючерсом на Индекс Мосбиржи.
        # Используем уже собранные market_data.
        # Повторного запроса benchmark нет.
        # ---------------------------------------------------------

        benchmark = next(
            (
                item
                for item in instruments
                if item.get("asset") == "IMOEX"
                and item.get("ticker") in market_data
            ),
            None
        )

        benchmark_candles = []

        if benchmark:

            benchmark_ticker = benchmark.get(
                "ticker"
            )

            benchmark_class_code = benchmark.get(
                "classCode"
            )

            benchmark_data = market_data.get(
                benchmark_ticker,
                {}
            )

            benchmark_records = benchmark_data.get(
                "records",
                []
            )

            benchmark_candles = benchmark_data.get(
                "candles",
                []
            )

            print()
            print(
                "📈 RS benchmark:",
                benchmark_ticker,
                benchmark_class_code
            )

            print(
                "RS benchmark trades:",
                len(benchmark_records)
            )

            print(
                "RS benchmark candles:",
                len(benchmark_candles)
            )

        else:

            print()
            print(
                "⚠️ RS benchmark IMOEX not found"
            )

        # ---------------------------------------------------------
        # INSTRUMENT ANALYSIS
        # ---------------------------------------------------------

        for ticker, data in market_data.items():

            item = data["item"]

            records = data["records"]

            candles = data["candles"]

            class_code = item.get(
                "classCode"
            )

            prices = []

            total_volume = 0

            money_volume = 0

            for trade in records:

                try:

                    price = float(
                        trade.get(
                            "price",
                            0
                        )
                    )

                    volume = float(
                        trade.get(
                            "volume",
                            0
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    continue

                if price <= 0:
                    continue

                prices.append(
                    price
                )

                total_volume += volume

                money_volume += (
                    price *
                    volume
                )

            if not prices:
                continue

            print(
                "DEBUG candles:",
                ticker,
                len(candles)
            )

            average_volume = (
                total_volume / 5
            )

            average_money_volume = 0

            previous_high = None

            previous_low = None

            if candles:

                previous_candles = candles[:-1]

                if previous_candles:

                    vols = [
                        c["volume"]
                        for c in previous_candles
                        if c["volume"] > 0
                    ]

                    money = [
                        c["money_volume"]
                        for c in previous_candles
                        if c["money_volume"] > 0
                    ]

                    if vols:

                        average_volume = (
                            sum(vols) /
                            len(vols)
                        )

                    if money:

                        average_money_volume = (
                            sum(money) /
                            len(money)
                        )

                    previous_high = max(
                        c["high"]
                        for c in previous_candles
                    )

                    previous_low = min(
                        c["low"]
                        for c in previous_candles
                    )

            current_price = prices[0]

            low = min(
                prices
            )

            high = max(
                prices
            )

            change_percent = (

                (
                    current_price -
                    low
                )

                /

                low

                *

                100

            ) if low else 0

            analysis = analyze_volume(

                ticker=ticker,

                price=current_price,

                volume=int(
                    total_volume
                ),

                average_volume=average_volume,

                change_percent=change_percent,

                low=low,

                high=high

            )

            # -----------------------------------------------------
            # RELATIVE STRENGTH
            # -----------------------------------------------------
            #
            # ВАЖНО:
            # Сравниваем только свечи с одинаковым timestamp.
            #
            # Нельзя использовать просто candles[0] / candles[-1],
            # потому что у инструмента и benchmark могут отсутствовать
            # отдельные 5-минутные свечи.
            #
            # Берём две последние общие свечи:
            #
            # common_times[-2] = previous
            # common_times[-1] = current
            #
            # Это гарантирует корректное сравнение одного и того же
            # временного интервала для инструмента и MX.
            # ---------------------------------------------------------

            if (
                benchmark_candles
                and candles
                and len(benchmark_candles) >= 2
                and len(candles) >= 2
            ):

                benchmark_by_time = {
                    candle.get("time"): candle
                    for candle in benchmark_candles
                    if candle.get("time")
                }

                instrument_by_time = {
                    candle.get("time"): candle
                    for candle in candles
                    if candle.get("time")
                }

                common_times = sorted(
                    set(benchmark_by_time)
                    & set(instrument_by_time)
                )

                if len(common_times) >= 2:

                    # RS WINDOW:
                    # сравниваем весь доступный общий интервал,
                    # а не только последнюю 5-минутную свечу.
                    previous_time = common_times[0]
                    current_time = common_times[-1]

                    benchmark_previous = (
                        benchmark_by_time[
                            previous_time
                        ].get(
                            "close",
                            0
                        )
                    )

                    benchmark_current = (
                        benchmark_by_time[
                            current_time
                        ].get(
                            "close",
                            0
                        )
                    )

                    instrument_previous = (
                        instrument_by_time[
                            previous_time
                        ].get(
                            "close",
                            0
                        )
                    )

                    instrument_current = (
                        instrument_by_time[
                            current_time
                        ].get(
                            "close",
                            0
                        )
                    )

                    print(
                        "RS aligned:",
                        ticker,
                        previous_time,
                        "->",
                        current_time
                    )

                    relative_strength = (
                        self.relative_strength_service.calculate(
                            instrument_previous=instrument_previous,
                            instrument_current=instrument_current,
                            benchmark_previous=benchmark_previous,
                            benchmark_current=benchmark_current
                        )
                    )

                    analysis.update(
                        relative_strength
                    )

                    print(
                        "DEBUG RS VALUES:",
                        ticker,
                        "instrument_return=",
                        relative_strength.get("instrument_return"),
                        "benchmark_return=",
                        relative_strength.get("benchmark_return"),
                        "relative_strength=",
                        relative_strength.get("relative_strength"),
                        "score=",
                        relative_strength.get("relative_strength_score"),
                        "signal=",
                        relative_strength.get("relative_strength_signal")
                    )

                else:

                    print(
                        "⚠️ RS: less than 2 common candles:",
                        ticker
                    )

                    analysis.update({

                        "instrument_return": 0.0,

                        "benchmark_return": 0.0,

                        "relative_strength": 0.0,

                        "relative_strength_score": 50.0,

                        "relative_strength_signal": "NEUTRAL"

                    })

            else:

                analysis.update({

                    "instrument_return": 0.0,

                    "benchmark_return": 0.0,

                    "relative_strength": 0.0,

                    "relative_strength_score": 50.0,

                    "relative_strength_signal": "NEUTRAL"

                })

            # -----------------------------------------------------
            # MOMENTUM
            # -----------------------------------------------------

            if candles:

                momentum = (
                    self.momentum_service.analyze(

                        candles[-1],

                        average_volume=average_volume,

                        average_money_volume=average_money_volume,

                        previous_high=previous_high,

                        previous_low=previous_low

                    )
                )

                analysis["momentum_score"] = (
                    momentum["momentum_score"]
                )

                analysis["momentum_signal"] = (
                    momentum["signal"]
                )

            # -----------------------------------------------------
            # BASIC DATA
            # -----------------------------------------------------

            analysis["trades"] = len(
                records
            )

            analysis["classCode"] = (
                class_code
            )

            analysis["money_volume_real"] = (
                money_volume
            )

            # -----------------------------------------------------
            # VOLUME SCORE
            # -----------------------------------------------------

            volume_score = (
                self.volume_score_service.calculate(

                    volume=int(
                        total_volume
                    ),

                    average_volume=average_volume,

                    money_volume=money_volume,

                    average_money_volume=average_money_volume

                )
            )

            analysis.update(
                volume_score
            )

            # -----------------------------------------------------
            # BREAKOUT
            # -----------------------------------------------------

            breakout = (
                self.breakout_service.analyze(

                    current_price=current_price,

                    previous_high=previous_high,

                    previous_low=previous_low,

                    volume_ratio=volume_score[
                        "volume_ratio"
                    ]

                )
            )

            analysis.update(
                breakout
            )

            # -----------------------------------------------------
            # BREAKOUT QUALITY
            # -----------------------------------------------------

            if candles:

                current_candle = candles[-1]

                breakout_quality = (
                    self.breakout_quality_service.analyze(

                        current_price=current_price,

                        open_price=current_candle[
                            "open"
                        ],

                        high_price=current_candle[
                            "high"
                        ],

                        low_price=current_candle[
                            "low"
                        ],

                        close_price=current_candle[
                            "close"
                        ],

                        previous_high=previous_high,

                        previous_low=previous_low

                    )
                )

                analysis.update(
                    breakout_quality
                )

            analysis["current_price"] = (
                current_price
            )

            result.append(
                analysis
            )

        # ---------------------------------------------------------
        # NO DATA
        # ---------------------------------------------------------

        if not result:

            print(
                "\n🌙 MARKET CLOSED / NO DATA"
            )

            print(
                "Scanner finished."
            )

            print(
                "No active trade data available."
            )

            return []

        # ---------------------------------------------------------
        # ИТОГОВЫЙ ТОРГОВЫЙ РЕЙТИНГ
        # ---------------------------------------------------------

        for item in result:

            item["trade_score"] = (
                self.trade_score_service.calculate(

                    volume_score=item.get(
                        "volume_score",
                        0
                    ),

                    momentum_score=item.get(
                        "momentum_score",
                        0
                    ),

                    signal=item.get(
                        "momentum_signal",
                        "NO_SIGNAL"
                    ),

                    breakout_score=item.get(
                        "breakout_score",
                        0
                    )

                )
            )

            signal_result = (
                self.signal_engine.analyze(
                    item
                )
            )

            item["final_signal"] = (
                signal_result["signal"]
            )

            item["signal"] = (
                signal_result["signal"]
            )

            item["confidence"] = (
                signal_result["confidence"]
            )

            item["reasons"] = (
                signal_result["reasons"]
            )

            trade_plan = (
                self.trade_plan_service.generate_plan(

                    current_price=item[
                        "current_price"
                    ],

                    signal=signal_result[
                        "signal"
                    ],

                    momentum_score=item.get(
                        "momentum_score",
                        0
                    ),

                    breakout_score=item.get(
                        "breakout_score",
                        0
                    )

                )
            )

            item.update(
                trade_plan
            )

            filter_result = (
                self.trade_filter_service.check(

                    signal=signal_result[
                        "signal"
                    ],

                    confidence=signal_result[
                        "confidence"
                    ],

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
                    ),

                    momentum_score=item.get(
                        "momentum_score",
                        0
                    ),

                    volume_score=item.get(
                        "volume_score",
                        0
                    )

                )
            )

            item["trade_allowed"] = (
                filter_result["allowed"]
            )

            item["trade_filter_level"] = (
                filter_result.get(
                    "level"
                )
            )

            item["trade_filter_reason"] = (
                filter_result["reason"]
            )

            confirmation = (
                self.trade_confirmation_service.confirm(

                    confidence=signal_result[
                        "confidence"
                    ],

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
                    ),

                    breakout_quality=item.get(
                        "breakout_quality_score",
                        item.get(
                            "breakout_quality",
                            0
                        )
                    ),

                    volume_ratio=item.get(
                        "volume_ratio",
                        0
                    ),

                    momentum_signal=item.get(
                        "momentum_signal",
                        "NO_SIGNAL"
                    ),

                    trade_allowed=item.get(
                        "trade_allowed",
                        False
                    )

                )
            )

            item["confirmation_score"] = (
                confirmation[
                    "confirmation_score"
                ]
            )

            item["confirmation_decision"] = (
                confirmation[
                    "decision"
                ]
            )

            item["confirmation_reasons"] = (
                confirmation[
                    "reasons"
                ]
            )

            trade_idea = (
                self.trade_idea_service.generate(
                    item
                )
            )

            item["trade_idea"] = (
                trade_idea
            )

        # ---------------------------------------------------------
        # TOP TRADE RANKING
        # ---------------------------------------------------------

        print(
            "DEBUG BEFORE RANKER"
        )

        for x in result:

            print(
                x.get("ticker"),
                x.get("final_signal"),
                x.get("confidence"),
                x.get("trade_score")
            )

        print(
            "DEBUG RANKER INPUT"
        )

        for x in result:

            print(
                x.get("ticker"),
                x.get("final_signal"),
                x.get("signal"),
                x.get("confidence")
            )

        print(
            "REAL OBJECT BEFORE RANKER"
        )

        for x in result:

            print(
                x.get("ticker"),
                id(x),
                x.get("final_signal"),
                x.get("signal")
            )

        ranked_trades = (
            self.trade_ranker_service.rank(

                result,

                limit=3

            )
        )

        ranked_trades = (
            self.portfolio_manager_service.select(

                ranked_trades,

                max_positions=3

            )
        )

        print(
            "DEBUG RANKED TRADES AFTER PORTFOLIO"
        )

        for x in ranked_trades:

            print(
                x.get("ticker"),
                x.get("final_signal"),
                x.get("confirmation_decision"),
                x.get("confidence")
            )

        # ---------------------------------------------------------
        # OUTCOME MANAGER CHECK OPEN TRADES
        # ---------------------------------------------------------

        market_prices = {}

        for item in result:

            ticker = item.get(
                "ticker"
            )

            price = item.get(
                "current_price"
            )

            if ticker and price:

                market_prices[ticker] = price

        print(
            "DEBUG MARKET PRICES:"
        )

        print(
            market_prices
        )

        closed_trades = (
            self.outcome_manager_service
            .evaluate_open_trades(
                market_prices
            )
        )

        if closed_trades:

            print(
                "📌 CLOSED TRADES:",
                len(closed_trades)
            )

        # ---------------------------------------------------------
        # TRADE JOURNAL
        # ---------------------------------------------------------

        for item in ranked_trades:

            decision = (
                item.get(
                    "confirmation_decision",
                    ""
                )
                or
                item.get(
                    "trade_score",
                    {}
                ).get(
                    "trade_grade",
                    ""
                )
            )

            if decision not in (
                "WATCH",
                "CONFIRMED",
                "ENTER"
            ):

                continue

            self.trade_journal_service.add_trade_idea(
                item
            )

        # ---------------------------------------------------------
        # SORT RESULT
        # ---------------------------------------------------------

        result.sort(

            key=lambda x:

            (
                x.get(
                    "trade_score",
                    {}
                ).get(
                    "score",
                    0
                )

                if isinstance(
                    x.get(
                        "trade_score"
                    ),
                    dict
                )

                else

                x.get(
                    "trade_score",
                    0
                )
            ),

            reverse=True

        )

        # ---------------------------------------------------------
        # TOP TRADE IDEAS
        # ---------------------------------------------------------

        print()

        print(
            "🔥 TOP TRADE IDEAS"
        )

        for item in ranked_trades:

            self.diagnostic_service.print_analysis(
                item
            )

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

                "RS:",

                item.get(
                    "relative_strength_score",
                    50.0
                ),

                "RS signal:",

                item.get(
                    "relative_strength_signal",
                    "NEUTRAL"
                ),

                "TRADE SCORE:",

                item["trade_score"],

                "signal:",

                item["final_signal"],

                "ENTRY:",
                item.get("entry"),

                "STOP:",
                item.get("stop_loss"),

                "TARGET:",
                item.get("take_profit"),

                "RR:",
                item.get("rr_ratio")

            )

        return result


if __name__ == "__main__":

    scanner = VolumeScanner()

    scanner.start()
