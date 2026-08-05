"""
Trader_7_12 Pro

Trade Journal Service

Версия 0.1

Назначение:
- запись торговых идей
- сохранение решений системы
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

        journal = self._load()


        record = {

            "time": datetime.now().isoformat(),

            "ticker": item.get(
                "ticker"
            ),

            "signal": item.get(
                "final_signal"
            ),

            "confidence": item.get(
                "confidence",
                0
            ),

            "confirmation_score": item.get(
                "confirmation_score",
                0
            ),

            "decision": item.get(
                "confirmation_decision"
            ),

            "entry": item.get(
                "entry"
            ),

            "stop": item.get(
                "stop"
            ),

            "target": item.get(
                "target"
            ),

            "rr": item.get(
                "rr_ratio",
                0
            ),

            "reasons": item.get(
                "reasons",
                []
            )

        }


        journal.append(
            record
        )


        self._save(
            journal
        )


        return record



    def get_history(self):

        return self._load()
