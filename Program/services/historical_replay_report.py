"""Instant offline report for the latest historical replay."""

import argparse
import json
from pathlib import Path


DEFAULT_FILE = Path("Docs/historical_replay/latest_results.json")


def _pct(item, endpoint, field):
    return float(
        ((item.get(f"outcome_{endpoint}") or {}).get(field, 0) or 0)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Show saved historical replay results without market/API calls."
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_FILE),
        help="Saved replay JSON file.",
    )
    args = parser.parse_args()

    path = Path(args.file)

    if not path.exists():
        print(f"ERROR: replay file not found: {path}")
        print("Run the historical replay once with the updated runner to create it.")
        raise SystemExit(1)

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("results", [])

    print("=" * 110)
    print("TRADER_7_12 PRO — SAVED HISTORICAL TRADES")
    print("=" * 110)
    print(
        f"DATES: {len(payload.get('dates', []))} | "
        f"CANDIDATES: {len(records)} | "
        f"FILE: {path}"
    )
    print("-" * 110)

    available = []

    for record in records:
        item = record.get("item") or {}
        outcome = item.get("outcome_13_00") or {}

        if not outcome.get("available"):
            continue

        trading_date = record.get("trading_date", "-")
        direction = str(item.get("direction", "-"))
        ticker = str(item.get("futures_ticker", "-"))
        spot = str(item.get("spot_ticker", "-"))
        confirmation = str(item.get("confirmation_time", "-"))
        window = str(item.get("confirmation_window", "NONE"))
        setup = str(item.get("setup", "-"))
        score = float(item.get("candidate_score", 0) or 0)
        directional = _pct(item, "13_00", "directional_return_percent")
        mfe = _pct(item, "13_00", "max_favorable_percent")

        available.append(
            {
                "date": trading_date,
                "ticker": ticker,
                "spot": spot,
                "direction": direction,
                "window": window,
                "confirmation": confirmation,
                "setup": setup,
                "score": score,
                "directional": directional,
                "mfe": mfe,
            }
        )

    for n, trade in enumerate(available, 1):
        print(
            f"{n:>2}. {trade['date']}  "
            f"{trade['ticker']:<7} {trade['spot']:<6} "
            f"{trade['direction']:<5} "
            f"{trade['window']:<5} "
            f"CONF {trade['confirmation']:<5} "
            f"{trade['setup']:<9} "
            f"SCORE {trade['score']:>6.2f}  "
            f"DIR {trade['directional']:>6.2f}%  "
            f"MFE {trade['mfe']:>6.2f}%"
        )

    print("-" * 110)

    if not available:
        print("OUTCOMES: 0")
        return

    wins = [x for x in available if x["directional"] > 0]
    avg_dir = sum(x["directional"] for x in available) / len(available)
    avg_mfe = sum(x["mfe"] for x in available) / len(available)

    print(f"OUTCOMES: {len(available)}")
    print(f"WIN RATE: {len(wins) / len(available) * 100:.1f}%")
    print(f"AVG DIR:  {avg_dir:.2f}%")
    print(f"AVG MFE:  {avg_mfe:.2f}%")

    print()
    print("=== BY CONFIRMATION WINDOW ===")

    for window in ("EARLY", "LATE", "NONE"):
        group = [x for x in available if x["window"] == window]

        if not group:
            print(f"{window}: OUTCOMES 0 | WIN RATE N/A")
            continue

        group_wins = [x for x in group if x["directional"] > 0]
        group_avg_dir = sum(x["directional"] for x in group) / len(group)
        group_avg_mfe = sum(x["mfe"] for x in group) / len(group)

        print(
            f"{window}: OUTCOMES {len(group)} | "
            f"WIN RATE {len(group_wins) / len(group) * 100:.1f}% | "
            f"AVG DIR {group_avg_dir:.2f}% | "
            f"AVG MFE {group_avg_mfe:.2f}%"
        )

    print()
    print("READ ONLY — no BCS/API, portfolio or order operations.")


if __name__ == "__main__":
    main()
