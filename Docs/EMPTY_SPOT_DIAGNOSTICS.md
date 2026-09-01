# Empty SPOT diagnostics

When the live SPOT candidate list is empty, the pipeline preserves scan diagnostics through a FUTURES_DIRECT carrier row. The UI removes that carrier from the SPOT list after extracting diagnostics, so no macro futures instrument becomes a trade candidate.