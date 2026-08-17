import os
import subprocess
import sys
from pathlib import Path

VENV_PYTHON = str(Path(__file__).resolve().parents[2] / ".venv" / "Scripts" / "python.exe")
print("sys.executable:", sys.executable, "VENV_PYTHON:", VENV_PYTHON, "cwd:", os.getcwd(), flush=True)

sys.path.insert(0, "scripts")
sys.path.insert(0, ".")
from dotenv import load_dotenv

load_dotenv(".env")

from find_cities_needing_tariff_validation import worklist  # noqa: E402

items = worklist()
ids = [i["city_id"] for i in items]
print(f"processing {len(ids)} cities, analytical-anchor-only (no web search)", flush=True)

ok, skip, fail = 0, 0, 0
for i, cid in enumerate(ids, 1):
    evidence_path = f"data/backups/evidence/{cid}.json"
    if not Path(evidence_path).exists():
        evidence_path = "data/backups/evidence/_empty.json"
    r = subprocess.run(
        [VENV_PYTHON, "scripts/validate_tariff_city.py", cid, "--evidence", evidence_path],
        capture_output=True, text=True, timeout=60,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    if "[ok]" in r.stdout:
        ok += 1
    elif "[skip]" in r.stdout or "[skip]" in r.stderr:
        skip += 1
    else:
        fail += 1
        print(f"FAIL {cid}: {r.stderr[-300:]}", flush=True)
    if i % 25 == 0:
        print(f"progress {i}/{len(ids)} ok={ok} skip={skip} fail={fail}", flush=True)

print(f"DONE total={len(ids)} ok={ok} skip={skip} fail={fail}", flush=True)
