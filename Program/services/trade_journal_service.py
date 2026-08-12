"""
Trader_7_12 Pro

Trade Journal Service

Версия 0.2

Назначение:

- запись торговых идей
- сохранение решений системы
- разделение WATCH / CONFIRMED / OPEN
- сохранение результатов закрытых сделок
- анализ результатов
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


    def add_trade_idea(
        self,
        item
    ):

        decision = item.get(
            "confirmation_decision",
            ""
        )

        if decision not in (
            "WATCH",
            "CONFIRMED",
            "ENTER"
        ):
            return None


        journal = self._load()


        # ---------------------------------------------------------
        # TRADE STATUS
        # ---------------------------------------------------------
        #
        # WATCH
        #     → идея находится под наблюдением
        #
        # CONFIRMED
        #     → сигнал подтверждён, но реального входа ещё нет
        #
        # ENTER
        #     → система дала команду на вход
        #     → позиция считается OPEN
        #
        # Это важно для Outcome Manager:
        # он должен контролировать только реальные OPEN сделки.
        # ---------------------------------------------------------

        if decision == "ENTER":

            status = "OPEN"

        elif decision == "CONFIRMED":

            status = "CONFIRMED"

        else:

            status = "WATCHING"


        record = {

            "time": datetime.now().isoformat(),

            "ticker": item.get(
                "ticker"
            ),

            "signal": item.get(
                "final_signal"
            ),

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
                0
            ),

            "status": status,

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


        # ---------------------------------------------------------
        # DEDUPLICATION
        # ---------------------------------------------------------
        #
        # Не создаём несколько одинаковых текущих идей
        # по одному инструменту / сигналу / решению.
        #
        # При этом WATCH, CONFIRMED и ENTER являются
        # разными стадиями и могут существовать отдельно.
        # ---------------------------------------------------------

        for trade in journal:

            if (
                trade.get("ticker") == record.get("ticker")
                and trade.get("signal") == record.get("signal")
                and trade.get("decision") == record.get("decision")
            ):

                # Не перезаписываем уже закрытую сделку.
                if trade.get("status") == "CLOSED":

                    continue


                trade.update(
                    {
                        "time": record.get("time"),
                        "signal": record.get("signal"),
                        "side": record.get("side"),
                        "status": record.get("status"),
                        "confidence": record.get("confidence"),
                        "confirmation_score": record.get(
                            "confirmation_score"
                        ),
                        "decision": record.get("decision"),
                        "entry": record.get("entry"),
                        "stop": record.get("stop"),
                        "target": record.get("target"),
                        "rr": record.get("rr"),
                        "reasons": record.get("reasons"),
                    }
                )


                self._save(
                    journal
                )


                return trade


        journal.append(
            record
        )


        self._save(
            journal
        )


        return record


    def get_history(self):

        return self._load()


    def update_trade(
        self,
        index,
        update_data
    ):

        journal = self._load()


        if index < 0 or index >= len(journal):

            return None


        journal[index].update(
            update_data
        )


        self._save(
            journal
        )


        return journal[index]
