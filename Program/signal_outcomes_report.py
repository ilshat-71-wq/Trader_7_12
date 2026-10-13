"""Print individual records and aggregate forward-candle performance for FINAL RADAR."""
from services.signal_outcome_journal import SignalOutcomeJournal


def _fmt(value):
    return "n/a" if value is None else f"{value:.3f}%"


def main():
    journal = SignalOutcomeJournal()
    print("SIGNAL OUTCOME JOURNAL")
    print("Database:", journal.db_path)
    print("Status counts:", journal.summary())

    summary = journal.performance_summary()
    print("\nAGGREGATE FORWARD OUTCOMES (BCS CLOSED M5)")
    print(summary["warning"])
    for horizon, metrics in summary["horizons"].items():
        gross, net = metrics["gross"], metrics["net"]
        print(
            f"{horizon}m: gross n={gross['sample_size']} "
            f"mean={_fmt(gross['mean_pct'])} median={_fmt(gross['median_pct'])} "
            f"win={_fmt(gross['win_rate_pct'])}; "
            f"net n={net['sample_size']} mean={_fmt(net['mean_pct'])} "
            f"median={_fmt(net['median_pct'])} win={_fmt(net['win_rate_pct'])}"
        )
        for group, values in summary["by_phase_direction"][horizon].items():
            g, n = values["gross"], values["net"]
            print(
                f"  {group}: gross n={g['sample_size']} mean={_fmt(g['mean_pct'])}; "
                f"net n={n['sample_size']} mean={_fmt(n['mean_pct'])} "
                f"win={_fmt(n['win_rate_pct'])}"
            )

    print("\nINDIVIDUAL SIGNALS")
    for row in journal.records():
        print(
            row["entry_time"], row["instrument_type"], row["ticker"],
            row["direction"], "entry=", row["entry_price"],
            "PROB=", row["probability"], "phase=", row["phase"] or "—",
            "status=", row["status"], "reason=", row["data_reason"] or "—",
        )
        for horizon, outcome in sorted(row["outcomes"].items(), key=lambda item: int(item[0])):
            print(
                f"  {horizon}m gross={outcome.get('gross_close_return_pct')}% "
                f"net={outcome.get('net_close_return_pct')}% "
                f"MFE={outcome.get('mfe_pct')}% MAE={outcome.get('mae_pct')}%"
            )


if __name__ == "__main__":
    main()
