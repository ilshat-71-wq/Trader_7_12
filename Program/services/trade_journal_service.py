"""
Trader_7_12 Pro

Trade Journal Service

Версия 0.3

Назначение:

- запись торговых идей
- сохранение решений системы
- lifecycle WATCH / CONFIRMED / EXECUTE
- преобразование EXECUTE -> ENTER для журнала
- контроль OPEN / CLOSED сделок
- защита закрытых сделок
- deduplication активной торговой идеи
- сохранение результатов закрытых сделок
"""

import json
from datetime import datetime
from pathlib import Path


class TradeJournalService:

    def __init__(self):

        self.path = Path(
            "data/trade_journal.json"
        )

        self.path.parent.mkdir(
            exist_ok=True
        )

        if not self.path.exists():

            self.path.write_text(
                "[]",
                encoding="utf-8"
            )

    # ---------------------------------------------------------
    # LOAD / SAVE
    # ---------------------------------------------------------

    def _load(self):

        return json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )

    def _save(self, data):

        self.path.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    def _status_for_decision(
        self,
        decision
    ):

        if decision == "EXECUTE":
            return "OPEN"

        if decision == "ENTER":
            return "OPEN"

        if decision == "CONFIRMED":
            return "CONFIRMED"

        return "WATCHING"

    # ---------------------------------------------------------
    # DECISION PRIORITY
    # ---------------------------------------------------------

    def _decision_priority(
        self,
        decision
    ):

        return {
            "WATCH": 1,
            "CONFIRMED": 2,
            "EXECUTE": 3,
            "ENTER": 3,
        }.get(
            decision,
            0
        )

    # ---------------------------------------------------------
    # ADD / UPDATE TRADE IDEA
    # ---------------------------------------------------------

    def add_trade_idea(
        self,
        item
    ):

        raw_decision = item.get(
            "confirmation_decision",
            ""
        )

        # -----------------------------------------------------
        # EXECUTE is the confirmation-layer command.
        #
        # ENTER is the journal-layer representation
        # of a real open position.
        # -----------------------------------------------------

        if raw_decision == "EXECUTE":

            decision = "ENTER"

        else:

            decision = raw_decision

        if decision not in (
            "WATCH",
            "CONFIRMED",
            "ENTER"
        ):

            return None

        ticker = item.get(
            "ticker"
        )

        signal = item.get(
            "final_signal"
        )

        journal = self._load()

        new_status = (
            self._status_for_decision(
                decision
            )
        )

        now = datetime.now().isoformat()

        # -----------------------------------------------------
        # FIND ACTIVE LIFECYCLE
        # -----------------------------------------------------
        #
        # Один ticker + один signal =
        # одна текущая торговая идея.
        #
        # CLOSED записи не трогаем.
        # -----------------------------------------------------

        active_trade = None

        for trade in journal:

            if trade.get(
                "status"
            ) == "CLOSED":

                continue

            if (
                trade.get("ticker") == ticker
                and trade.get("signal") == signal
            ):

                active_trade = trade
                break

        # -----------------------------------------------------
        # NEW RECORD
        # -----------------------------------------------------

        record = {

            "time": now,

            "ticker": ticker,

            "signal": signal,

            "side": item.get(
                "side"
            ),

            "confidence": item.get(
                "confidence",
                0
            ),

            "confirmation_score": item.get(
                "confirmation_score",
                0
            ),

            "decision": decision,

            "entry": item.get(
                "entry"
            ),

            "stop": item.get(
                "stop_loss"
            ),

            "target": item.get(
                "take_profit"
            ),

            "rr": item.get(
                "rr_ratio",
                item.get(
                    "rr",
                    0
                )
            ),

            "status": new_status,

            "exit_price": None,

            "result": None,

            "profit_points": None,

            "closed_at": None,

            "exit_reason": None,

            "reasons": item.get(
                "reasons",
                []
            )

        }

        # -----------------------------------------------------
        # NO ACTIVE TRADE
        # -----------------------------------------------------

        if active_trade is None:

            journal.append(
                record
            )

            self._save(
                journal
            )

            return record

        # -----------------------------------------------------
        # ACTIVE TRADE EXISTS
        # -----------------------------------------------------
        #
        # WATCH / CONFIRMED / ENTER are stages of the
        # same lifecycle.
        #
        # However, once a trade is OPEN, a later WATCH
        # must never downgrade it back to WATCHING.
        # -----------------------------------------------------

        current_status = active_trade.get(
            "status"
        )

        current_decision = active_trade.get(
            "decision",
            ""
        )

        # -----------------------------------------------------
        # OPEN PROTECTION
        # -----------------------------------------------------

        if current_status == "OPEN":

            # Do not downgrade an OPEN position.

            if decision in (
                "WATCH",
                "CONFIRMED"
            ):

                return active_trade

            # ENTER again means refresh the active
            # entry parameters without creating
            # a duplicate record.

            if decision == "ENTER":

                active_trade.update(
                    {
                        "time": now,
                        "decision": "ENTER",
                        "entry": record.get(
                            "entry"
                        ),
                        "stop": record.get(
                            "stop"
                        ),
                        "target": record.get(
                            "target"
                        ),
                        "rr": record.get(
                            "rr"
                        ),
                        "confidence": record.get(
                            "confidence"
                        ),
                        "confirmation_score": record.get(
                            "confirmation_score"
                        ),
                        "reasons": record.get(
                            "reasons"
                        ),
                    }
                )

                self._save(
                    journal
                )

                return active_trade

        # -----------------------------------------------------
        # LIFECYCLE UPGRADE
        # -----------------------------------------------------

        current_priority = (
            self._decision_priority(
                current_decision
            )
        )

        new_priority = (
            self._decision_priority(
                decision
            )
        )

        # -----------------------------------------------------
        # Do not downgrade an existing lifecycle.
        # -----------------------------------------------------

        if new_priority < current_priority:

            return active_trade

        # -----------------------------------------------------
        # Update active lifecycle.
        # -----------------------------------------------------

        active_trade.update(
            {
                "time": now,
                "decision": decision,
                "entry": record.get(
                    "entry"
                ),
                "stop": record.get(
                    "stop"
                ),
                "target": record.get(
                    "target"
                ),
                "rr": record.get(
                    "rr"
                ),
                "status": new_status,
                "confidence": record.get(
                    "confidence"
                ),
                "confirmation_score": record.get(
                    "confirmation_score"
                ),
                "reasons": record.get(
                    "reasons"
                ),
            }
        )

        self._save(
            journal
        )

        return active_trade

    # ---------------------------------------------------------
    # HISTORY
    # ---------------------------------------------------------

    def get_history(self):

        return self._load()

    # ---------------------------------------------------------
    # UPDATE TRADE
    # ---------------------------------------------------------

    def update_trade(
        self,
        index,
        update_data
    ):

        journal = self._load()

        if (
            index < 0
            or index >= len(journal)
        ):

            return None

        journal[index].update(
            update_data
        )

        self._save(
            journal
        )

        return journal[index]
