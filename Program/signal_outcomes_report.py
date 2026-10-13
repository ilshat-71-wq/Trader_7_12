"""Print the persistent FINAL RADAR signal-outcome journal."""
from services.signal_outcome_journal import SignalOutcomeJournal


def main():
    journal = SignalOutcomeJournal()
    print("SIGNAL OUTCOME JOURNAL")
    print("Database:", journal.db_path)
    print("Status counts:", journal.summary())
    for row in journal.records():
        print(
            row["entry_time"], row["instrument_type"], row["ticker"],
            row["direction"], "entry=", row["entry_price"],
            "PROB=", row["probability"], "status=", row["status"],
            "reason=", row["data_reason"] or "—",
        )
        for horizon, result in sorted(row["outcomes"].items(), key=lambda item: int(item[0])):
            print(
                f"  {horizon}m gross={result.get('gross_close_return_pct')}% "
                f"net={result.get('net_close_return_pct')}% "
                f"MFE={result.get('mfe_pct')}% MAE={result.get('mae_pct')}%"
            )


if __name__ == "__main__":
    main()
