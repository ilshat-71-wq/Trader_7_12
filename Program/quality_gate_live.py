"""Run deterministic checks plus the real Trader_7_12 scanner."""
from __future__ import annotations
import compileall
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def main() -> int:
    print("Trader_7_12 REAL-DATA QUALITY GATE")
    print("Policy: missing/unverified data is never converted to GREEN.")
    ok = compileall.compile_dir(str(ROOT), quiet=1)
    print(f"1 COMPILEALL: {'GREEN' if ok else 'RED'}")
    if not ok:
        return 1
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT)
    print(f"2 PYTEST: {'GREEN' if result.returncode == 0 else 'RED'}")
    if result.returncode:
        return result.returncode
    result = subprocess.run([sys.executable, "-c", "import main; print('main import: GREEN')"], cwd=ROOT)
    print(f"3 IMPORT SMOKE: {'GREEN' if result.returncode == 0 else 'RED'}")
    if result.returncode:
        return result.returncode
    result = subprocess.run([sys.executable, "main.py"], cwd=ROOT)
    print(f"4 LIVE SCANNER PROCESS: {'GREEN' if result.returncode == 0 else 'RED'}")
    if result.returncode:
        return result.returncode
    print("5 DATA TRUTH: LIVE DIAGNOSTICS ABOVE ARE AUTHORITATIVE")
    print("6 QUALITY GATE: GREEN (process only; never overrides data diagnostics)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
