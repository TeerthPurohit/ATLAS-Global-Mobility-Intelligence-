"""Download WorldMove per-city data into data/raw/worldmove_{category}/.

Replaces download_worldmove_india.py, which only ever fetched the `pop`
category and hardcoded a "first world" country allow-list as the city filter.

WorldMove serves four per-city categories off the same key
(`{worldmove_id}_{country_code}_{city_name}`):

    pop   .npy   (rows, cols) float64      population per 1km grid cell
    poi   .npy   (rows, cols, 34) float32  POI counts per category
    grid  .json  {cell_index: [lon, lat]}  true cell-centre coordinates
    traj  .npy   (n_agents, 48) int64      cell index per half-hour slot, one day

Verified against the live API 2026-08-13. Two things worth knowing before
you use this data:

  * `poi` is served but **empty** — all zeros for every city sampled (14/14,
    spanning 3-cell Medina to 1748-cell Galveston). Don't build features on it
    without re-checking.
  * `traj` covers a single representative 24h day (48 half-hour slots), not a
    calendar. There is no multi-day history, so lag_24h/lag_168h-style features
    do not exist for these cities.

Trajectories are ~2.5GB across the 522-city corpus. Downloads are resumable:
files already on disk are skipped, so a failed run can just be re-run.

    python scripts/download_worldmove.py --category traj
    python scripts/download_worldmove.py --category grid --all
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import requests

BASE_URL = "https://fi.ee.tsinghua.edu.cn/worldmove"
BUNDLE_URL = f"{BASE_URL}/assets/js/39848085.ae8aadc4.js"
REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"

# category -> (file extension, expected Content-Type fragment)
CATEGORIES = {
    "pop": ("npy", "octet-stream"),
    "poi": ("npy", "octet-stream"),
    "traj": ("npy", "octet-stream"),
    "grid": ("json", "json"),
}

# The existing pop corpus doubles as the default city list, so every category
# stays aligned to the same 522 cities without re-deriving a scope filter.
DEFAULT_CITY_DIR = RAW_ROOT / "worldmove_data"

KEY_PATTERN = re.compile(r"(?:(?:hzy-)?\d+_[A-Z]{2,3}_[A-Za-z0-9_\-']+)")


def output_dir(category: str) -> Path:
    # keep the original pop location so nothing downstream has to move
    return DEFAULT_CITY_DIR if category == "pop" else RAW_ROOT / f"worldmove_{category}"


def city_keys_from_disk() -> list[str]:
    return sorted(p.stem for p in DEFAULT_CITY_DIR.glob("*.npy"))


def city_keys_from_site(session: requests.Session) -> list[str]:
    response = session.get(BUNDLE_URL, timeout=60)
    response.raise_for_status()
    return sorted(set(KEY_PATTERN.findall(response.text)))


def download_key(session: requests.Session, category: str, key: str, destination: Path) -> int:
    extension, expected_type = CATEGORIES[category]
    url = f"{BASE_URL}/api/file/{category}/{key}.{extension}"

    response = session.get(url, timeout=600, stream=True)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if expected_type not in content_type:
        raise RuntimeError(f"expected {expected_type} for {key}, got {content_type!r}")

    # write to a temp path first so an interrupted run never leaves a truncated
    # file that the next (resumable) run would skip as already-downloaded
    partial = destination.with_suffix(destination.suffix + ".part")
    written = 0
    with open(partial, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
                written += len(chunk)
    partial.replace(destination)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--category", choices=sorted(CATEGORIES), default="traj")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch every city WorldMove publishes (~1625) instead of the "
             "522 already present in data/raw/worldmove_data.",
    )
    parser.add_argument("--limit", type=int, help="Stop after N cities (for testing).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    category = args.category
    extension, _ = CATEGORIES[category]

    destination_dir = output_dir(category)
    destination_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    keys = city_keys_from_site(session) if args.all else city_keys_from_disk()
    if args.limit:
        keys = keys[: args.limit]

    print(f"category={category} cities={len(keys)} -> {destination_dir}")

    downloaded = skipped = failed = 0
    total_bytes = 0
    for index, key in enumerate(keys, start=1):
        destination = destination_dir / f"{key}.{extension}"
        if destination.exists():
            skipped += 1
            continue
        try:
            total_bytes += download_key(session, category, key, destination)
            downloaded += 1
            if downloaded % 25 == 0:
                print(f"[{index}/{len(keys)}] {downloaded} downloaded, "
                      f"{total_bytes / 1e6:.0f} MB, last={key}")
        except Exception as exc:
            failed += 1
            print(f"[{index}/{len(keys)}] FAILED {key}: {exc}")
        time.sleep(0.2)

    print(f"\nDONE {category}: {downloaded} downloaded ({total_bytes / 1e6:.0f} MB), "
          f"{skipped} already present, {failed} failed")


if __name__ == "__main__":
    main()
