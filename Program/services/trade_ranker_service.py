"""
Trader_7_12 Pro

Trade Ranker Service

Версия 0.4

Назначение:

- выбор лучших торговых идей
- фильтрация слабых сигналов
- обязательный STRONG_TRADE filter gate
- приоритет EXECUTE > WATCH
- сортировка по качеству
- подготовка TOP кандидатов
"""


class TradeRankerService:

    def rank(self, items, limit=3):

        ranked = []

        confirmation_priority = {
            "EXECUTE": 2,
            "WATCH": 1,
            "EARLY": 0,
            "REJECT": 0,
        }

        for item in items:

            signal = (
                item.get("final_signal")
                or item.get("momentum_signal")
                or "NO_SIGNAL"
            )

            confidence = item.get(
                "confidence",
                0
            )

            rr = item.get(
                "rr",
                item.get(
                    "rr_ratio",
                    0
                )
            )

            confirmation_decision = item.get(
                "confirmation_decision",
                "REJECT"
            )

            trade_allowed = item.get(
                "trade_allowed",
                False
            )

            trade_filter_level = item.get(
                "trade_filter_level",
                "BLOCK"
            )

            # -----------------------------------------------------
            # NO SIGNAL
            # -----------------------------------------------------

            if signal == "NO_SIGNAL":

                print(
                    "RANKER DROP NO_SIGNAL:",
                    item.get("ticker"),
                    signal
                )

                continue

            # -----------------------------------------------------
            # MINIMUM CONFIDENCE
            # -----------------------------------------------------

            if confidence < 55:

                print(
                    "RANKER DROP CONFIDENCE:",
                    item.get("ticker"),
                    confidence
                )

                continue

            # -----------------------------------------------------
            # MINIMUM RR
            # -----------------------------------------------------

            if rr and rr < 2:

                print(
                    "RANKER DROP RR:",
                    item.get("ticker"),
                    rr
                )

                continue

            # -----------------------------------------------------
            # CONFIRMATION GATE
            #
            # EARLY is NOT a trade candidate.
            # Only WATCH and EXECUTE may reach TOP.
            # -----------------------------------------------------

            if confirmation_decision not in (
                "WATCH",
                "EXECUTE",
            ):

                print(
                    "RANKER DROP CONFIRMATION LEVEL:",
                    item.get("ticker"),
                    confirmation_decision
                )

                continue

            # -----------------------------------------------------
            # TRADE FILTER GATE
            #
            # WATCHLIST means:
            # observe only.
            #
            # STRONG_TRADE means:
            # candidate is allowed into TOP ranking.
            # -----------------------------------------------------

            if trade_filter_level != "STRONG_TRADE":

                print(
                    "RANKER DROP FILTER LEVEL:",
                    item.get("ticker"),
                    trade_filter_level
                )

                continue

            # -----------------------------------------------------
            # FINAL TRADE ALLOWED GATE
            # -----------------------------------------------------

            if not trade_allowed:

                print(
                    "RANKER DROP TRADE FILTER:",
                    item.get("ticker")
                )

                continue

            ranked.append(item)

        # ---------------------------------------------------------
        # TRADE SCORE VALUE
        # ---------------------------------------------------------

        def trade_score_value(item):

            trade_score = item.get(
                "trade_score",
                0
            )

            if isinstance(
                trade_score,
                dict
            ):

                return trade_score.get(
                    "trade_score",
                    trade_score.get(
                        "score",
                        0
                    )
                )

            return trade_score

        # ---------------------------------------------------------
        # FINAL SORT
        # ---------------------------------------------------------

        ranked.sort(

            key=lambda x: (

                confirmation_priority.get(
                    x.get(
                        "confirmation_decision",
                        "REJECT"
                    ),
                    0
                ),

                x.get(
                    "confirmation_score",
                    0
                ),

                x.get(
                    "confidence",
                    0
                ),

                trade_score_value(x),

                x.get(
                    "rr",
                    x.get(
                        "rr_ratio",
                        0
                    )
                ),

                x.get(
                    "relative_strength_score",
                    50
                ),

                x.get(
                    "volume_score",
                    0
                ),

                abs(
                    x.get(
                        "momentum_score",
                        0
                    )
                )

            ),

            reverse=True

        )

        return ranked[:limit]
