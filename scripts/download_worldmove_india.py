from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Iterable

import requests


INDEX_URL = "https://fi.ee.tsinghua.edu.cn/worldmove/data/pop"
BUNDLE_URL = "https://fi.ee.tsinghua.edu.cn/worldmove/assets/js/39848085.ae8aadc4.js"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "raw" / "worldmove_data"

# Approximation for "first world" / developed-country cities.
# Keep this explicit so the script does not depend on an ambiguous browser click flow.
FIRST_WORLD_COUNTRY_CODES = {
    "US",
    "CA",
    "GB",
    "FR",
    "DE",
    "AU",
    "NZ",
    "JP",
    "KR",
    "NL",
    "BE",
    "CH",
    "AT",
    "DK",
    "FI",
    "SE",
    "NO",
    "IE",
    "LU",
    "IT",
    "ES",
    "PT",
    "SG",
    "IL",
    "IS",
    "MT",
    "CY",
    "CZ",
    "EE",
    "GR",
    "HR",
    "HU",
    "LT",
    "LV",
    "PL",
    "SK",
    "SI",
    "AD",
    "SM",
    "MC",
    "LI",
    "AE",
    "QA",
    "KW",
    "BH",
    "OM",
    "SA",
    "HK",
    "TW",
}

KEY_PATTERN = re.compile(r"(?:(?:hzy-)?\d+_[A-Z]{2,3}_[A-Za-z0-9_\-']+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download WorldMove population files into data/raw/worldmove_data."
    )
    parser.add_argument(
        "--scope",
        action="append",
        choices=["india", "first_world", "all"],
        help="City scopes to download. Default: india and first_world.",
    )
    return parser.parse_args()


def extract_city_keys(session: requests.Session) -> list[str]:
    response = session.get(BUNDLE_URL, timeout=60)
    response.raise_for_status()
    keys = sorted(set(KEY_PATTERN.findall(response.text)))
    return keys


def country_code_for_key(key: str) -> str:
    parts = key.split("_", 2)
    if len(parts) < 3:
        return ""
    return parts[1]


def city_name_for_key(key: str) -> str:
    parts = key.split("_", 2)
    if len(parts) < 3:
        return key
    return parts[2]


def filter_keys(keys: Iterable[str], scopes: list[str]) -> list[str]:
    if "all" in scopes:
        return list(keys)

    include_india = "india" in scopes
    include_first_world = "first_world" in scopes

    selected = []
    for key in keys:
        country_code = country_code_for_key(key)
        if include_india and country_code == "IN":
            selected.append(key)
            continue
        if include_first_world and country_code in FIRST_WORLD_COUNTRY_CODES:
            selected.append(key)
    return selected


def download_key(session: requests.Session, key: str) -> Path:
    url = f"{INDEX_URL.replace('/data/pop', '')}/api/file/pop/{key}.npy"
    destination = OUTPUT_DIR / f"{key}.npy"
    response = session.get(url, timeout=120, stream=True)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" in content_type:
        raise RuntimeError(f"Expected a binary .npy response, got HTML for {key}")

    with open(destination, "wb") as file_handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file_handle.write(chunk)

    return destination


def main() -> None:
    args = parse_args()
    scopes = args.scope or ["india", "first_world"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    keys = extract_city_keys(session)
    selected_keys = filter_keys(keys, scopes)

    print(f"Found {len(keys)} total WorldMove cities")
    print(f"Selected {len(selected_keys)} cities for scopes: {', '.join(scopes)}")

    for index, key in enumerate(selected_keys, start=1):
        print(f"[{index}/{len(selected_keys)}] Downloading {key}")
        try:
            destination = download_key(session, key)
            print(f"✓ Saved: {destination}")
        except Exception as exc:
            print(f"✗ FAILED: {key}")
            print(exc)
        time.sleep(0.2)

    print("\nDONE")


if __name__ == "__main__":
    main()
