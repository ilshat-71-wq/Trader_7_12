"""
Trader_7_12 Pro

Trade Decision Engine v0.9

Назначение:

- финальный отбор торговых возможностей
- фильтрация слабых сигналов
- пропуск только подтвержденных торговых сигналов
- защита от TRADE при NO_SIGNAL
- разделение WATCH / EARLY / TRADE
- проверка объема
- проверка ликвидности
- проверка согласованности направления
- защита от TRADE при LOW confidence
"""


class TradeDecisionEngine:

    def __init__(self):

        self.version = "0.9"

    # -------------------------------------------------
    # Главная проверка сделки
    # -------------------------------------------------

    def evaluate(
        self,
        row
    ):

        score = getattr(
            row,
            "trade_score",
            0
        )

        rating = getattr(
            row,
            "rating",
            0
        )

        momentum = getattr(
            row,
            "momentum_score",
            0
        )

        money_volume = getattr(
            row,
            "money_volume",
            0
        )

        volume_ratio = getattr(
            row,
            "volume_ratio",
            0
        )

        direction = getattr(
            row,
            "direction",
            ""
        )

        signal = getattr(
            row,
            "signal",
            ""
        )

        breakout_quality = getattr(
            row,
            "breakout_quality",
            getattr(
                row,
                "breakout_quality_score",
                0
            )
        )

        # -------------------------------------------------
        # NORMALIZE NUMBERS
        # -------------------------------------------------

        try:
            score = float(score)
        except (
            TypeError,
            ValueError
        ):
            score = 0.0

        try:
            rating = float(rating)
        except (
            TypeError,
            ValueError
        ):
            rating = 0.0

        try:
            momentum = float(momentum)
        except (
            TypeError,
            ValueError
        ):
            momentum = 0.0

        try:
            money_volume = float(
                money_volume
            )
        except (
            TypeError,
            ValueError
        ):
            money_volume = 0.0

        try:
            volume_ratio = float(
                volume_ratio
            )
        except (
            TypeError,
            ValueError
        ):
            volume_ratio = 0.0

        try:
            breakout_quality = float(
                breakout_quality
            )
        except (
            TypeError,
            ValueError
        ):
            breakout_quality = 0.0

        # -------------------------------------------------
        # 1. DIRECTION
        # -------------------------------------------------

        if direction not in (
            "LONG",
            "SHORT"
        ):

            return {
                "decision": "SKIP",
                "reason": "No valid direction"
            }

        # -------------------------------------------------
        # 2. SIGNAL
        # -------------------------------------------------

        active_signals = (
            "LONG_WATCH",
            "EARLY_LONG",
            "STRONG_LONG",
            "SHORT_WATCH",
            "EARLY_SHORT",
            "STRONG_SHORT"
        )

        if signal not in active_signals:

            return {
                "decision": "SKIP",
                "reason": "No active signal"
            }

        # -------------------------------------------------
        # 3. DIRECTION CONSISTENCY
        # -------------------------------------------------

        long_signals = (
            "LONG_WATCH",
            "EARLY_LONG",
            "STRONG_LONG"
        )

        short_signals = (
            "SHORT_WATCH",
            "EARLY_SHORT",
            "STRONG_SHORT"
        )

        if signal in long_signals:

            if direction != "LONG":

                return {
                    "decision": "SKIP",
                    "reason": "Direction mismatch"
                }

        if signal in short_signals:

            if direction != "SHORT":

                return {
                    "decision": "SKIP",
                    "reason": "Direction mismatch"
                }

        # -------------------------------------------------
        # 4. BASIC SCORE
        # -------------------------------------------------

        if score < 35:

            return {
                "decision": "SKIP",
                "reason": "Low trade score"
            }

        # -------------------------------------------------
        # 5. RATING
        # -------------------------------------------------

        if rating < 40:

            return {
                "decision": "SKIP",
                "reason": "Low rating"
            }

        # -------------------------------------------------
        # 6. LIQUIDITY
        # -------------------------------------------------

        if money_volume < 3_000_000:

            return {
                "decision": "SKIP",
                "reason": "Low liquidity"
            }

        # -------------------------------------------------
        # 7. VOLUME
        # -------------------------------------------------

        if volume_ratio < 1.2:

            return {
                "decision": "SKIP",
                "reason": "No volume expansion"
            }

        # -------------------------------------------------
        # 8. MOMENTUM
        # -------------------------------------------------

        if direction == "LONG":

            if momentum < 45:

                return {
                    "decision": "SKIP",
                    "reason": "Weak long momentum"
                }

        elif direction == "SHORT":

            if momentum > -45:

                return {
                    "decision": "SKIP",
                    "reason": "Weak short momentum"
                }

        # -------------------------------------------------
        # 9. WATCH / EARLY / STRONG
        # -------------------------------------------------

        # LONG_WATCH / SHORT_WATCH:
        #
        # Это наблюдение, а НЕ торговая команда.
        #
        # Даже если momentum сильный, такой сигнал
        # должен ждать дополнительного подтверждения.

        watch_signals = (
            "LONG_WATCH",
            "SHORT_WATCH"
        )

        if signal in watch_signals:

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": "LOW",
                "reasons": [
                    "Active watch signal",
                    "Waiting for stronger confirmation"
                ]
            }

        # -------------------------------------------------
        # 10. EARLY SIGNAL
        # -------------------------------------------------

        early_signals = (
            "EARLY_LONG",
            "EARLY_SHORT"
        )

        if signal in early_signals:

            # Early setup должен иметь заметный momentum
            # и хороший trade score.

            if score < 55:

                return {
                    "decision": "WATCH",
                    "ticker": getattr(
                        row,
                        "ticker",
                        ""
                    ),
                    "direction": direction,
                    "signal": signal,
                    "trade_score": score,
                    "rating": rating,
                    "momentum_score": momentum,
                    "volume_ratio": volume_ratio,
                    "money_volume": money_volume,
                    "breakout_quality": breakout_quality,
                    "confidence": "LOW",
                    "reasons": [
                        "Early setup",
                        "Trade score below confirmation threshold"
                    ]
                }

            if direction == "LONG":

                if momentum < 55:

                    return {
                        "decision": "WATCH",
                        "ticker": getattr(
                            row,
                            "ticker",
                            ""
                        ),
                        "direction": direction,
                        "signal": signal,
                        "trade_score": score,
                        "rating": rating,
                        "momentum_score": momentum,
                        "volume_ratio": volume_ratio,
                        "money_volume": money_volume,
                        "breakout_quality": breakout_quality,
                        "confidence": "LOW",
                        "reasons": [
                            "Early long setup",
                            "Momentum needs confirmation"
                        ]
                    }

            elif direction == "SHORT":

                if momentum > -55:

                    return {
                        "decision": "WATCH",
                        "ticker": getattr(
                            row,
                            "ticker",
                            ""
                        ),
                        "direction": direction,
                        "signal": signal,
                        "trade_score": score,
                        "rating": rating,
                        "momentum_score": momentum,
                        "volume_ratio": volume_ratio,
                        "money_volume": money_volume,
                        "breakout_quality": breakout_quality,
                        "confidence": "LOW",
                        "reasons": [
                            "Early short setup",
                            "Momentum needs confirmation"
                        ]
                    }

        # -------------------------------------------------
        # 11. STRONG SIGNAL
        # -------------------------------------------------

        strong_signals = (
            "STRONG_LONG",
            "STRONG_SHORT"
        )

        if signal not in strong_signals:

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": "LOW",
                "reasons": [
                    "Setup requires confirmation"
                ]
            }

        # -------------------------------------------------
        # 12. STRONG TRADE SCORE
        # -------------------------------------------------

        if score < 70:

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": "LOW",
                "reasons": [
                    "Strong signal but insufficient trade score"
                ]
            }

        # -------------------------------------------------
        # 13. STRONG RATING
        # -------------------------------------------------

        if rating < 55:

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": "LOW",
                "reasons": [
                    "Strong signal but rating is insufficient"
                ]
            }

        # -------------------------------------------------
        # 14. STRONG VOLUME
        # -------------------------------------------------

        if volume_ratio < 1.5:

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": "LOW",
                "reasons": [
                    "Strong signal but volume confirmation is insufficient"
                ]
            }

        # -------------------------------------------------
        # 15. STRONG MOMENTUM
        # -------------------------------------------------

        if direction == "LONG":

            if momentum < 60:

                return {
                    "decision": "WATCH",
                    "ticker": getattr(
                        row,
                        "ticker",
                        ""
                    ),
                    "direction": direction,
                    "signal": signal,
                    "trade_score": score,
                    "rating": rating,
                    "momentum_score": momentum,
                    "volume_ratio": volume_ratio,
                    "money_volume": money_volume,
                    "breakout_quality": breakout_quality,
                    "confidence": "LOW",
                    "reasons": [
                        "Strong long signal but momentum is insufficient"
                    ]
                }

        elif direction == "SHORT":

            if momentum > -60:

                return {
                    "decision": "WATCH",
                    "ticker": getattr(
                        row,
                        "ticker",
                        ""
                    ),
                    "direction": direction,
                    "signal": signal,
                    "trade_score": score,
                    "rating": rating,
                    "momentum_score": momentum,
                    "volume_ratio": volume_ratio,
                    "money_volume": money_volume,
                    "breakout_quality": breakout_quality,
                    "confidence": "LOW",
                    "reasons": [
                        "Strong short signal but momentum is insufficient"
                    ]
                }

        # -------------------------------------------------
        # 16. BREAKOUT QUALITY
        # -------------------------------------------------

        if breakout_quality < 35:

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": "MEDIUM",
                "reasons": [
                    "Strong signal but breakout confirmation is insufficient"
                ]
            }

        # -------------------------------------------------
        # 17. CONFIDENCE
        # -------------------------------------------------

        confidence = "MEDIUM"

        if (
            score >= 80
            and rating >= 70
            and volume_ratio >= 2
            and breakout_quality >= 50
        ):

            confidence = "HIGH"

        elif (
            score >= 70
            and rating >= 60
            and volume_ratio >= 1.5
            and breakout_quality >= 35
        ):

            confidence = "MEDIUM"

        else:

            confidence = "LOW"

        # -------------------------------------------------
        # 18. LOW CONFIDENCE CANNOT TRADE
        # -------------------------------------------------

        if confidence == "LOW":

            return {
                "decision": "WATCH",
                "ticker": getattr(
                    row,
                    "ticker",
                    ""
                ),
                "direction": direction,
                "signal": signal,
                "trade_score": score,
                "rating": rating,
                "momentum_score": momentum,
                "volume_ratio": volume_ratio,
                "money_volume": money_volume,
                "breakout_quality": breakout_quality,
                "confidence": confidence,
                "reasons": [
                    "Strong signal but confidence is too low"
                ]
            }

        # -------------------------------------------------
        # 19. TRADE
        # -------------------------------------------------

        reasons = [
            "Strong momentum",
            "Volume confirmation",
            "Strong trade score"
        ]

        if rating >= 70:

            reasons.append(
                "High rating"
            )

        if volume_ratio >= 2:

            reasons.append(
                "Volume spike"
            )

        if breakout_quality >= 50:

            reasons.append(
                "Breakout confirmed"
            )

        return {
            "decision": "TRADE",
            "ticker": getattr(
                row,
                "ticker",
                ""
            ),
            "direction": direction,
            "signal": signal,
            "trade_score": score,
            "rating": rating,
            "momentum_score": momentum,
            "volume_ratio": volume_ratio,
            "money_volume": money_volume,
            "breakout_quality": breakout_quality,
            "confidence": confidence,
            "reasons": reasons
        }

    # -------------------------------------------------
    # Массовая обработка
    # -------------------------------------------------

    def rank(
        self,
        rows
    ):

        results = []

        for row in rows:

            result = self.evaluate(
                row
            )

            if result.get(
                "decision"
            ) == "TRADE":

                results.append(
                    result
                )

        results.sort(
            key=lambda x: (
                x.get(
                    "trade_score",
                    0
                ),
                x.get(
                    "momentum_score",
                    0
                ),
                x.get(
                    "rating",
                    0
                ),
                x.get(
                    "volume_ratio",
                    0
                )
            ),
            reverse=True
        )

        return results