"""Trader_7_12 Pro - live read-only morning scanner runner.

Runs the existing Morning Trading Pipeline and prints the final shortlist.
No orders are submitted.
"""

from services.morning_trading_pipeline_service import MorningTradingPipelineService


class MorningScannerRunner:
    VERSION = "0.2"

    def __init__(self, pipeline=None):
        self.pipeline = pipeline or MorningTradingPipelineService()

    def run(self, limit=3):
        """Run the real morning pipeline in read-only mode."""
        return self.pipeline.scan(limit=limit)

    @staticmethod
    def print_results(results):
        print("=" * 76)
        print("TRADER_7_12 PRO - MORNING SCANNER RUNNER v0.2")
        print("READ ONLY — ORDERS ARE NOT SENT")
        print("=" * 76)

        if not results:
            print("NO FINAL TRADE CANDIDATES")
            return

        for index, item in enumerate(results, 1):
            print(f"#{index}")
            print(f"  futures: {item.get('futures_ticker', '-')}")
            print(f"  spot: {item.get('spot_ticker', '-')}")
            print(f"  direction: {item.get('direction', '-')}")
            print(f"  entry: {item.get('entry', item.get('entry_price', '-'))}")
            print(f"  stop: {item.get('stop_loss', '-')}")
            print(f"  target: {item.get('take_profit', '-')}")
            print(f"  RR: {item.get('rr_ratio', '-')}")
            print(f"  score: {item.get('candidate_score', item.get('final_score', '-'))}")
            print(f"  radar: {item.get('radar_score', '-')}")
            print(f"  confirmation: {item.get('confirmation_score', '-')}")
            print(f"  RS: {item.get('relative_strength', '-')}")
            print(f"  trades: {item.get('trade_count', '-')}")
            print(f"  money volume: {item.get('money_volume', '-')}")
            print(f"  futures change: {item.get('price_change_percent', '-')}%")
            print(f"  setup: {item.get('setup', '-')}")
            print(f"  setup state: {item.get('setup_state', '-')}")
            print("-" * 76)


def main():
    runner = MorningScannerRunner()
    results = runner.run(limit=3)
    runner.print_results(results)


if __name__ == "__main__":
    main()
