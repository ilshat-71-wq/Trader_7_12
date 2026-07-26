from scanner.scanner_engine import ScannerEngine

scanner = ScannerEngine()

rows = scanner.load()

print("Всего инструментов:", len(rows))
print()

for row in rows[:20]:
    print(
        row.ticker,
        "|",
        row.short_name,
        "| Short:",
        row.short_allowed,
        "| Margin:",
        row.margin_allowed,
        "| Sector:",
        row.sector,
        "| Cap:",
        int(row.market_cap),
    )