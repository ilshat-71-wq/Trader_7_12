"""Command-line runner for historical morning replay."""

import argparse

from services.morning_replay_service import MorningReplayService


DEFAULT_DATE = "2026-08-14"
DEFAULT_TICKER = "YDEX"
DEFAULT_CLASS_CODE = "SPBRU"
DEFAULT_DIRECTION = "SHORT"


def main():
    parser = argparse.ArgumentParser(
        description="Replay the existing SPOT M5 setup logic on a completed morning."
    )
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    parser.add_argument("--class-code", default=DEFAULT_CLASS_CODE)
    parser.add_argument("--direction", choices=("LONG", "SHORT"), default=DEFAULT_DIRECTION)
    parser.add_argument(
        "--checkpoints",
        default="07:15,07:30,08:00,08:30,09:00,09:30,10:00",
        help="Comma-separated Moscow times.",
    )
    args = parser.parse_args()

    checkpoints = [item.strip() for item in args.checkpoints.split(",") if item.strip()]

    service = MorningReplayService()
    results = service.replay_setup(
        ticker=args.ticker,
        class_code=args.class_code,
        direction=args.direction,
        trading_date=args.date,
        checkpoints=checkpoints,
    )
    service.print_results(results)


if __name__ == "__main__":
    main()
