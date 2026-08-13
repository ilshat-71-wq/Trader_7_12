"""
Trader_7_12 Pro
Instrument Morning Radar - live test
"""

from services.instrument_morning_radar_service import (
    InstrumentMorningRadarService
)


def main():

    print()
    print("=" * 72)
    print("TRADER_7_12 PRO - INSTRUMENT MORNING RADAR TEST")
    print("=" * 72)

    service = InstrumentMorningRadarService()

    print()
    print("Running scan...")
    print()

    try:
        results = service.scan()
    except Exception as exc:
        print()
        print("SCAN ERROR:", exc)
        raise

    if not isinstance(results, list):
        print("ERROR: scan() returned:", type(results))
        return

    print()
    print("=" * 72)
    print("RESULTS")
    print("=" * 72)

    for i, result in enumerate(results, 1):

        if not isinstance(result, dict):
            print(f"{i}. INVALID RESULT: {result}")
            continue

        ticker = result.get("ticker", "UNKNOWN")
        direction = result.get("direction", "UNKNOWN")
        radar = result.get("radar_score", 0)
        radar_signal = result.get(
            "signal",
            "UNKNOWN"
        )

        rs = result.get(
            "relative_strength",
            0.0
        )

        rs_score = result.get(
            "relative_strength_score",
            50.0
        )

        rs_signal = result.get(
            "relative_strength_signal",
            "NEUTRAL"
        )

        print(
            f"{i}. "
            f"{ticker:<7} "
            f"{direction:<6} "
            f"RADAR={float(radar):>6.2f} "
            f"RS={float(rs):>8.4f} "
            f"RS_SCORE={float(rs_score):>6.2f} "
            f"{rs_signal:<10} "
            f"{radar_signal}"
        )

    print()
    print("=" * 72)
    print("COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
