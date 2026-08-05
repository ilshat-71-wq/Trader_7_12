"""
Trader_7_12 Pro

Trade Idea Service

Версия 0.1

Назначение:
- формирование торговой идеи
- подготовка результата для трейдера
- вывод направления
- вход
- стоп
- цель
- риск/прибыль
"""


class TradeIdeaService:


    def generate(self, item):

        if not item.get("trade_plan"):
            return None


        return {

            "ticker": item.get("ticker"),

            "direction": item.get("direction"),

            "signal": item.get("final_signal"),

            "confidence": item.get("confidence"),

            "entry": item.get("entry"),

            "stop": item.get("stop_loss"),

            "target": item.get("take_profit"),

            "rr": item.get("rr_ratio"),

            "reasons": item.get("reasons", [])

        }
