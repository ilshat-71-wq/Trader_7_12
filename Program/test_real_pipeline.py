from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.candle_service import CandleService
from services.momentum_service import MomentumService
from services.rating_service import RatingService
from services.volume_score_service import VolumeScoreService
from services.breakout_service import BreakoutService
from services.breakout_quality_service import BreakoutQualityService
from services.signal_engine import SignalEngine
from scanner.trade_decision_engine import TradeDecisionEngine
from services.final_trade_service import FinalTradeService
from models.scanner_row import ScannerRow
from datetime import datetime, timezone


TICKERS = {
    "SBER",
    "LKOH",
    "ROSN",
    "TATN",
    "PLZL",
    "SNGSP",
    "YDEX",
}


print()
print("=" * 72)
print("TRADER_7_12 PRO — REAL PIPELINE TEST v0.2")
print("=" * 72)


instrument_service = InstrumentService()
quote_service = QuoteService()
trade_service = TradeService()
candle_service = CandleService()
momentum_service = MomentumService()
rating_service = RatingService()
volume_score_service = VolumeScoreService()
breakout_service = BreakoutService()
breakout_quality_service = BreakoutQualityService()
signal_engine = SignalEngine()
decision_engine = TradeDecisionEngine()


final_service = FinalTradeService(
    deposit=1_000_000,
    risk_percent=1.0,
    min_rr=1.5,
    max_position_percent=20.0
)


if not instrument_service.connect():
    print("❌ Нет соединения BCS")
    raise SystemExit(1)


instruments = instrument_service.load_stocks()


selected = [
    x
    for x in instruments
    if x.get("ticker") in TICKERS
]


print()
print("Найдено рабочих инструментов:", len(selected))
print()


for instrument in selected:

    ticker = instrument.get("ticker")
    class_code = instrument.get("classCode")
    lot_size = instrument.get("lotSize", 1)

    print()
    print("-" * 72)
    print(
        f"{ticker} | class={class_code} | lotSize={lot_size}"
    )
    print("-" * 72)

    try:

        quote = quote_service.load(
            ticker,
            class_code
        )

        if not isinstance(quote, dict):
            print("⛔ Quote отсутствует")
            continue

        last = float(
            quote.get("last", 0)
        )

        change = float(
            quote.get("changeRate", 0)
        )

        print(
            "PRICE:",
            last,
            "CHANGE:",
            change
        )


        trades = trade_service.load(
            ticker,
            class_code
        )

        if isinstance(trades, dict):
            records = trades.get(
                "records",
                []
            )
        else:
            records = []

        print(
            "TRADES:",
            len(records)
        )


        volume = 0
        money_volume = 0

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
                trade_volume * price
            )


        print(
            "VOLUME:",
            volume
        )

        print(
            "MONEY VOLUME:",
            money_volume
        )


        candles = candle_service.build_candles(
            records,
            timeframe_minutes=5
        )

        print(
            "CANDLES:",
            len(candles)
        )


        momentum = {}

        if candles:

            previous_candles = candles[:-1]

            previous_volumes = [
                c["volume"]
                for c in previous_candles
                if c["volume"] > 0
            ]

            previous_money = [
                c["money_volume"]
                for c in previous_candles
                if c["money_volume"] > 0
            ]

            average_volume = (
                sum(previous_volumes)
                / len(previous_volumes)
                if previous_volumes
                else 0
            )

            average_money_volume = (
                sum(previous_money)
                / len(previous_money)
                if previous_money
                else 0
            )

            previous_high = (
                max(
                    c["high"]
                    for c in previous_candles
                )
                if previous_candles
                else None
            )

            previous_low = (
                min(
                    c["low"]
                    for c in previous_candles
                )
                if previous_candles
                else None
            )

            last_candle = candles[-1]

            momentum = momentum_service.analyze(
                last_candle,
                average_volume=average_volume,
                average_money_volume=average_money_volume,
                previous_high=previous_high,
                previous_low=previous_low
            )


        print()
        print(
            "MOMENTUM:",
            momentum
        )


        rating = rating_service.calculate(
            last=last,
            change=change,
            volume=volume,
            money_volume=money_volume
        )


        print(
            "RATING:",
            rating
        )


        volume_analysis = volume_score_service.calculate(volume=volume, average_volume=average_volume, money_volume=money_volume, average_money_volume=average_money_volume)

        breakout = breakout_service.analyze(current_price=last, previous_high=previous_high, previous_low=previous_low, volume_ratio=volume_analysis.get("volume_ratio", 0))

        breakout_quality = {}
        if candles:
            current_candle = candles[-1]
            breakout_quality = breakout_quality_service.analyze(current_price=last, open_price=current_candle.get("open", 0), high_price=current_candle.get("high", 0), low_price=current_candle.get("low", 0), close_price=current_candle.get("close", 0), previous_high=previous_high, previous_low=previous_low)

        signal_analysis = {
            **quote,
            "ticker": ticker,
            "volume_score": float(
                volume_analysis.get("volume_score", 0)
            ),
            "momentum_score": float(
                momentum.get("momentum_score", 0)
                if isinstance(momentum, dict)
                else 0
            ),
            "breakout_score": float(breakout.get("breakout_score", 0) if isinstance(breakout, dict) else 0),
            "breakout_quality_score": float(breakout_quality.get("breakout_quality_score", 0) if isinstance(breakout_quality, dict) else 0),
            "breakout_strength": float(
                momentum.get("breakout_strength", 0)
                if isinstance(momentum, dict)
                else 0
            ),
            "trade_score": {
                "trade_score": float(
                    rating.get("rating", 0)
                    if isinstance(rating, dict)
                    else rating
                )
            },
            "relative_strength_score": 50.0
        }

        signal = signal_engine.analyze(
            signal_analysis
        )


        print()
        print(
            "SIGNAL:",
            signal
        )


        row = ScannerRow(
            ticker=ticker,
            lot_size=int(
                float(
                    lot_size or 1
                )
            ),
            last=last,
            change=change,
            volume=volume,
            money_volume=money_volume,
            rating=rating,
            volume_ratio=momentum.get(
                "volume_ratio",
                0
            ),
            volume_score=signal_analysis.get(
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
            trade_score=signal_analysis.get(
                "trade_score",
                {}
            ).get(
                "trade_score",
                0
            ),
            direction=(
                "LONG"
                if signal.get("signal", "").endswith("LONG")
                else "SHORT"
                if signal.get("signal", "").endswith("SHORT")
                else ""
            ),
            confidence=signal.get(
                "confidence",
                ""
            ),
            reasons=signal.get(
                "reasons",
                []
            ),
            signal=signal.get(
                "signal",
                "NO_SIGNAL"
            )
        )


        print()
        print(
            "ROW:",
            row
        )


        decision = decision_engine.evaluate(
            row
        )


        print()
        print(
            "DECISION:",
            decision
        )


        if decision.get("decision") == "TRADE":

            idea = final_service.build(
                row,
                decision
            )

            print()
            print("🔥 FINAL IDEA:")

            print(
                idea
            )

        else:

            print()
            print(
                "⛔ FINAL TRADE: NO TRADE"
            )


    except Exception as e:

        print()
        print(
            "❌ PIPELINE ERROR:",
            ticker,
            repr(e)
        )


print()
print("=" * 72)
print("REAL PIPELINE TEST FINISHED")
print("=" * 72)
