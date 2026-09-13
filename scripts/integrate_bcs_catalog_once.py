from pathlib import Path

TARGET = Path("Program/services/futures_oi_marketdata_scanner_service.py")
IMPORT = "from api.bcs_underlying_catalog import preferred_instruments\n"
START_MARKER = "    @staticmethod\n    def _underlying_lookup_aliases"
END_MARKER = "    @staticmethod\n    def _session_turnover"

NEW_BLOCK = '''    @staticmethod
    def _underlying_lookup_aliases(ticker):
        """Return only real BCS ticker spellings; no synthetic instrument names."""
        normalized = "".join(ch for ch in str(ticker or "").upper() if ch.isalnum())
        aliases = {
            "USDRUB": ("USDRUB_TOM", "USDRUB_TOD"),
            "EURRUB": ("EURRUB_TOM", "EURRUB_TOD"),
            "CNYRUB": ("CNYRUB_TOM", "CNYRUB_TOD"),
            "GLDRUBTOM": ("GLDRUB_TOM",),
        }
        preferred = preferred_instruments(ticker)
        if preferred:
            return tuple(item["ticker"] for item in preferred if item.get("ticker"))
        return aliases.get(normalized, (str(ticker).upper(),))

    def _underlying_quotes(self, contracts):
        """Resolve futures to a real BCS economic underlying and real quote only.

        A catalog entry is only a preferred lookup pair. It never fabricates a
        quote: BCS metadata must confirm the exact ticker/classCode before the
        instrument is accepted.
        """
        requested = {}
        family_tickers = {}
        for item in contracts:
            family = self._text(item, "oi_root", "futures_root").upper()
            if not family:
                continue
            canonical = self._family_to_underlying(family).upper()
            normalized_ticker = self._normalize_mapping_text(canonical)
            ticker_aliases = {
                "USDRUB": "USDRUB", "USDRUBTOM": "USDRUB",
                "EURRUB": "EURRUB", "EURRUBTOM": "EURRUB",
                "CNYRUB": "CNYRUB", "CNYRUBTOM": "CNYRUB",
                "GLDRUB": "GLDRUB_TOM", "GLDRUBTOM": "GLDRUB_TOM",
            }
            canonical = ticker_aliases.get(normalized_ticker, canonical)
            family_tickers[family] = canonical
            item_class = self._text(item, "underlying_class_code", "underlyingClassCode")
            entry = requested.setdefault(canonical, {"ticker": canonical, "classCode": "", "families": set()})
            entry["families"].add(family)
            if item_class and not entry["classCode"]:
                entry["classCode"] = item_class

        lookup_tickers = []
        for canonical, entry in requested.items():
            candidates = preferred_instruments(canonical)
            if not candidates and entry.get("classCode"):
                candidates = ({"ticker": canonical, "classCode": entry["classCode"]},)
            if not candidates:
                candidates = tuple({"ticker": ticker} for ticker in self._underlying_lookup_aliases(canonical))
            entry["candidates"] = tuple(candidates)
            for candidate in entry["candidates"]:
                ticker = str(candidate.get("ticker") or "").strip().upper()
                if ticker and ticker not in lookup_tickers:
                    lookup_tickers.append(ticker)

        lookup_records = 0
        exact_matches = 0
        lookup_batches = 0
        records_by_ticker = {}
        for start in range(0, len(lookup_tickers), self.ENRICH_BATCH_SIZE):
            batch = lookup_tickers[start:start + self.ENRICH_BATCH_SIZE]
            lookup_batches += 1
            try:
                records = self.api.get_instruments_by_tickers(batch)
            except Exception as exc:
                print("⚠️ Underlying metadata lookup failed:", type(exc).__name__)
                continue
            if not isinstance(records, list):
                continue
            lookup_records += len(records)
            for record in records:
                if not self._is_real_underlying_record(record):
                    continue
                actual_ticker = self._text(record, "ticker", "secCode", "securityCode").strip().upper()
                class_code = self._text(record, "classCode", "class_code", "classcode") or self._select_underlying_class_code(record)
                if actual_ticker and class_code:
                    records_by_ticker.setdefault(actual_ticker, []).append((record, class_code))

        instruments = []
        for canonical, entry in requested.items():
            accepted = None
            for candidate in entry["candidates"]:
                wanted_ticker = str(candidate.get("ticker") or "").strip().upper()
                wanted_class = str(candidate.get("classCode") or "").strip().upper()
                for record, actual_class in records_by_ticker.get(wanted_ticker, ()):
                    if wanted_class and actual_class.upper() != wanted_class:
                        continue
                    accepted = (wanted_ticker, actual_class, record)
                    break
                if accepted:
                    break
            if not accepted:
                continue
            actual_ticker, class_code, record = accepted
            entry["classCode"] = class_code
            entry["bcsTicker"] = actual_ticker
            entry["mappingSource"] = "BCS_EXACT_CATALOG" if preferred_instruments(canonical) else "BCS_EXACT_LOOKUP"
            exact_matches += 1
            instruments.append({"ticker": actual_ticker, "classCode": class_code})

        self._underlying_class_codes = {key: value["classCode"] for key, value in requested.items() if value.get("classCode") and value.get("bcsTicker")}
        self._underlying_bcs_tickers = {key: value["bcsTicker"] for key, value in requested.items() if value.get("bcsTicker")}
        self._underlying_mapping_source = {key: value["mappingSource"] for key, value in requested.items() if value.get("mappingSource")}
        self._underlying_family_tickers = family_tickers
        self._underlying_metadata_diagnostics = {
            "underlying_requested": len(requested),
            "underlying_class_codes": len(self._underlying_class_codes),
            "underlying_class_code_missing": max(0, len(requested) - len(self._underlying_class_codes)),
            "underlying_metadata_lookup_batches": lookup_batches,
            "underlying_metadata_lookup_records": lookup_records,
            "underlying_exact_matches": exact_matches,
            "underlying_semantic_matches": 0,
        }
        if not instruments:
            return {}
        try:
            quotes = self.api.get_quotes_batch(instruments)
        except Exception as exc:
            print("⚠️ Underlying quotes lookup failed:", type(exc).__name__)
            return {}
        return {self._text(q, "ticker", "secCode", "securityCode").upper(): q for q in quotes if isinstance(q, dict)}

'''

text = TARGET.read_text()
if IMPORT not in text:
    marker = "from services.futures_oi_scanner_service import FuturesOIScannerService\n"
    if marker not in text:
        raise SystemExit("Expected scanner import marker not found")
    text = text.replace(marker, marker + IMPORT, 1)

start = text.find(START_MARKER)
end = text.find(END_MARKER, start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit("Expected underlying method block not found")

text = text[:start] + NEW_BLOCK + text[end:]
TARGET.write_text(text)
print(f"Integrated BCS exact underlying catalog into {TARGET}")
