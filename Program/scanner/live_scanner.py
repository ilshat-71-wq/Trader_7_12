import os
import time
from datetime import datetime

from scanner.market_scanner import MarketScanner

class LiveScanner:
    def __init__(self, interval=3):
        self.interval = interval
        self.scanner = MarketScanner()

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def run(self):
        try:
            while True:
                self.clear()
                print("=" * 58)
                print("               TRADER_7_12 LIVE SCANNER")
                print("=" * 58)
                print("Время:", datetime.now().strftime("%H:%M:%S"))
                print()

                contracts = self.scanner.get_active_futures()
                if not contracts:
                    print("Нет активных контрактов.")
                elif self.scanner.api.authorize():
                    instruments = [{"ticker": c["ticker"], "classCode": c["classCode"]} for c in contracts]
                    quotes = self.scanner.api.get_quotes(instruments)
                    records = quotes.get("records", [])
                    signals = self.scanner.engine.rank(records)
                    print(f"{'№':<3}{'Тикер':<8}{'Цена':>12}{'%':>9}{'Score':>8}{'Сигнал':>10}")
                    print("-"*58)
                    for i,s in enumerate(signals,1):
                        print(f"{i:<3}{s['ticker']:<8}{s['price']:>12.2f}{s['change']:>9.2f}{s['score']:>8}{s['direction']:>10}")
                print(f"\nСледующее обновление через {self.interval} сек.  Ctrl+C - выход.")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nСканер остановлен.")

if __name__ == "__main__":
    LiveScanner().run()
