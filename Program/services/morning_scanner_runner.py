"""Trader_7_12 Pro - live read-only morning scanner runner.

Runs the existing Morning Trading Pipeline and prints the final shortlist.
No orders are submitted.
"""

import argparse

from services.morning_trading_pipeline_service import MorningTradingPipelineService


class MorningScannerRunner:
    VERSION = "0.4"

    def __init__(self, pipeline=None):
        self.pipeline = pipeline or MorningTradingPipelineService()

    def run(self, limit=3):
        """Run the real morning pipeline in read-only mode."""
        return self.pipeline.scan(limit=limit)

    @staticmethod
    def print_results(results):
        print("=" * 96)
        print("TRADER_7_12 PRO - MORNING SCANNER RUNNER v0.4")
        print("READ ONLY — NO ORDERS")
        print("=" * 96)

        if not results:
            print("NO FINAL CANDIDATES")
            return

        print(
            f"{'#':>3} {'FUTURES':<10} {'SPOT':<8} {'DIR':<7} "
            f"{'RADAR':>8} {'CONF':>8} {'RS':>8} {'MONEY VOL':>16} {'SCORE':>8}"
        )
        print("-" * 96)

        for index, item in enumerate(results, 1):
            print(
                f"{index:>3} "
                f"{str(item.get('futures_ticker', '-')):<10} "
                f"{str(item.get('spot_ticker', '-')):<8} "
                f"{str(item.get('direction', '-')):<7} "
                f"{float(item.get('radar_score', 0) or 0):>8.2f} "
                f"{float(item.get('confirmation_score', 0) or 0):>8.2f} "
                f"{float(item.get('relative_strength', 0) or 0):>8.2f} "
                f"{float(item.get('money_volume', 0) or 0):>16,.0f} "
                f"{float(item.get('candidate_score', item.get('final_score', 0)) or 0):>8.2f}"
            )

        print()
        print("Pipeline: SPOT RADAR -> FUTURES CONFIRMATION -> TOP CANDIDATES")
        print("No risk sizing, SL/TP calculation or order execution is performed.")
        print("=" * 96)


def main():
    parser = argparse.ArgumentParser(
        description="Run the read-only Trader_7_12 morning scanner."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of final candidates (default: 3).",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be >= 0")

    runner = MorningScannerRunner()
    results = runner.run(limit=args.limit)
    runner.print_results(results)


if __name__ == "__main__":
    main()
