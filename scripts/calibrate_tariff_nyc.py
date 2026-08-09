"""Credibility anchor for the LLM-tariff methodology (ADR-011).

Prompts the LLM for New York City's fare structure using ONLY its general
world knowledge -- deliberately withholding the real NYC fare regression
(scripts/nyc_fare_anchor.py) that generate_tariff_profile.py shows for every
OTHER city -- then measures how far that blind guess is from NYC's real,
measured fares (rules.md rule 2: never estimate a number that looks
plausible when a real one can be measured).

This produces the one real, bounded number every `llm_anchored` tariff
profile's `reason` string can point to: "this method reproduces real NYC
fares to within N% (measured, N=1 city)."

Usage: python scripts/calibrate_tariff_nyc.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "rag"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from llm_client import chat_completion  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"
OUT_PATH = REPO_ROOT / "docs" / "tariff_calibration.json"
_MODEL = "gpt-5.4-nano"
_SAMPLE_ROWS = 50_000

_BLIND_PROMPT = """Using ONLY your general knowledge of New York City's taxi/ride-hailing market \
(Yellow Cab, Uber, Lyft) -- not any data provided here -- estimate a linear fare structure: base \
fare, per-mile rate, per-minute rate, and minimum fare, all in USD.

Respond with ONLY a JSON object, no prose, no markdown fences:
{"base_fare": <number USD>, "per_mile": <number USD>, "per_min": <number USD>, \
"min_fare": <number USD>, "notes": "<one sentence: what you're reasoning from>"}
"""


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rstrip("`").strip()
    return json.loads(text)


def blind_guess() -> dict:
    resp = chat_completion(
        model=_MODEL, messages=[{"role": "user", "content": _BLIND_PROMPT}],
        temperature=0.2, max_completion_tokens=300,
    )
    raw = (resp.choices[0].message.content or "").strip()
    return _parse_json_response(raw)


def measure_mape(guess: dict, sample_rows: int = _SAMPLE_ROWS) -> dict:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        df = con.execute(
            f"""
            SELECT trip_distance, trip_duration_minutes, total_amount
            FROM int_trips_enriched
            WHERE total_amount > 0.5 AND trip_distance > 0 AND trip_duration_minutes > 0
            USING SAMPLE {sample_rows} ROWS
            """
        ).df()
    finally:
        con.close()

    predicted = np.maximum(
        guess["base_fare"] + guess["per_mile"] * df["trip_distance"] + guess["per_min"] * df["trip_duration_minutes"],
        guess["min_fare"],
    )
    actual = df["total_amount"].to_numpy()
    mape = float(np.mean(np.abs(predicted - actual) / actual) * 100)
    return {"mape_pct": round(mape, 1), "n": int(len(df))}


def main() -> None:
    guess = blind_guess()
    print(f"LLM blind guess for NYC: {guess}")
    result = measure_mape(guess)
    print(f"Measured MAPE vs real NYC fares: {result['mape_pct']}% (n={result['n']})")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"blind_guess": guess, **result}, indent=2))
    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    main()
