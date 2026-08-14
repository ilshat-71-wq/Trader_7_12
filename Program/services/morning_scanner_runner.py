"""Trader_7_12 Pro - live read-only morning scanner runner.

Runs the existing Morning Trading Pipeline and prints the final shortlist.
No orders are submitted.
"""

from services.morning_trading_pipeline_service import MorningTradingPipelineService


class MorningScannerRunner:
    VERSION = "0.1"

    def __init__(self, pipeline=None):
        self.pipeline = pipeline or MorningTradingPipelineService()

    def run(self, limit=3):
        return self.pipeline.run(limit=limit)

    @staticmethod
    def print_results(results):
        print("=" * 76)
        print("TRADER_7_12 PRO - MORNING SCANNER RUNNER v0.1")
        print("READ ONLY — ORDERS ARE NOT SENT")
        print("=" * 76)

        if not results:
            print("NO FINAL TRADE CANDIDATES")
            return

        for index, item in enumerate(results, 1):
            print(f"#{index}")
            print(f"  ticker: {item.get('futures_ticker')}")
            print(f"  direction: {item.get('direction')}")
            print(f"  entry: {item.get('entry_price')}")
            print(f"  stop: {item.get('stop_loss')}")
            print(f"  target: {item.get('take_profit')}")
            print(f"  score: {item.get('final_score')}")
            print(f"  status: {item.get('status')}")
            print("-" * 76)


def main():
    runner = MorningScannerRunner()
    results = runner.run(limit=3)
    runner.print_results(results)


if __name__ == "__main__":
    main()
