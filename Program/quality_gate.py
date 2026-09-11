"""Trader_7_12 local quality gate.

Runs deterministic checks before the live scanner. It never fabricates market data
and never converts missing data into GREEN.
"""
from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(label: str, args: list[str]) -> bool:
    print(f"\n=== {label} ===")
    result = subprocess.run(args, cwd=ROOT, text=True)
    print(f"=== {label}: {'GREEN' if result.returncode == 0 else 'RED'} ===")
    return result.returncode == 0


def main() -> int:
    print("Trader_7_12 REAL-DATA QUALITY GATE")
    print(f"ROOT: {ROOT}")
    print("Policy: missing/unverified data is never converted to GREEN.")

    compile_ok = compileall.compile_dir(str(ROOT), quiet=1)
    print(f"\n=== COMPILEALL: {'GREEN' if compile_ok else 'RED'} ===")
    if not compile_ok:
        return 1

    tests_ok = run("PYTEST", [sys.executable, "-m", "pytest", "-q"])
    if not tests_ok:
        return 1

    print("\n=== IMPORT SMOKE ===")
    smoke = subprocess.run(
        [sys.executable, "-c", "from main import main; print('main import: GREEN')"],
        cwd=ROOT,
        text=True,
    )
    print(f"=== IMPORT SMOKE: {'GREEN' if smoke.returncode == 0 else 'RED'} ===")
    if smoke.returncode != 0:
        return 1

    print("\n=== QUALITY GATE: GREEN ===")
    print("Automated code checks passed. Live-data truthfulness must be confirmed by the live scanner output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
