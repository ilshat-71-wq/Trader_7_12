"""Trader_7_12 Pro - live read-only opportunity watchlist runner."""

import argparse

from services.morning_trading_pipeline_service import MorningTradingPipelineService


class MorningScannerRunner:
    VERSION = "0.5"

    def __init__(self, pipeline=None):
        self.pipeline = pipeline or MorningTradingPipelineService()

    def run(self, limit=3):
        """Run the real SPOT-first pipeline in read-only mode."""
        return self.pipeline.scan(limit=limit)

    @staticmethod
    def print_results(results):
        print("=" * 108)
        print("TRADER_7_12 PRO - SPOT OPPORTUNITY WATCHLIST v0.5")
        print("READ ONLY — NO ORDERS")
        print("=" * 108)

        if not results:
            print("NO WATCHLIST CANDIDATES")
            print("TOP-2/3 is an opportunity watchlist, not an entry gate.")
            return

        print(
            f"{'#':>3} {'SPOT':<12} {'DIR':<7} {'OPPORTUNITY':>12} "
            f"{'SETUP':>10} {'PACE':>8} {'RS':>8} {'SPOT MONEY':>16}"
        )
        print("-" * 108)

        for index, item in enumerate(results, 1):
            print(
                f"{index:>3} "
                f"{str(item.get('spot_ticker', '-')):<12} "
                f"{str(item.get('direction', '-')):<7} "
                f"{float(item.get('opportunity_score', item.get('session_rank_score', 0)) or 0):>12.2f} "
                f"{str(item.get('setup_state', '-')).upper():>10} "
                f"{float(item.get('spot_session_activity_ratio', 0) or 0):>8.2f} "
                f"{float(item.get('relative_strength', 0) or 0):>8.2f} "
                f"{float(item.get('spot_money_volume', 0) or 0):>16,.0f}"
            )

        print()
        print("Pipeline: FAST SPOT SCREEN -> DEEP SPOT H1/RS/M5 -> TOP 2-3 BASE ASSETS")
        print("SETUP STATE is reported separately; WAIT/WATCH may remain in the TOP watchlist.")
        print("Futures are mapping-only; no futures confirmation, ranking or order execution is performed.")
        print("=" * 108)


def main():
    parser = argparse.ArgumentParser(description="Run the read-only Trader_7_12 SPOT opportunity watchlist.")
    parser.add_argument("--limit", type=int, default=3, help="Maximum number of watchlist candidates (default: 3).")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be >= 0")

    runner = MorningScannerRunner()
    results = runner.run(limit=args.limit)
    runner.print_results(results)


if __name__ == "__main__":
    main()
