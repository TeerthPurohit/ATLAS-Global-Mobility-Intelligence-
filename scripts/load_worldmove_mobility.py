"""Aggregate WorldMove trajectories + grid coordinates into DuckDB.

Layer 0 ingestion (dbt models downstream do the shaping). Writes three tables:

  worldmove_city          one row per city: agent count, population, grid shape
  worldmove_city_grid     one row per (city, cell): true lon/lat + population
  worldmove_cell_halfhour one row per (city, cell, slot): departures/arrivals/occupancy
  worldmove_cell_flows    one row per (city, from_cell, to_cell): trips

Source data (see scripts/download_worldmove.py):
  data/raw/worldmove_traj/{key}.npy   (n_agents, 48) int64, cell index per
                                       half-hour slot across ONE representative day
  data/raw/worldmove_grid/{key}.json  {cell_index: [lon, lat]}
  data/raw/worldmove_data/{key}.npy   (rows, cols) float64 population

A "trip" here is a cell-to-cell movement between consecutive slots: if agent i
is in cell A at slot t and cell B != A at slot t+1, that is one departure from A
at slot t and one arrival at B at slot t+1. This is the direct analogue of
zone_hourly_demand's pickup count, at 1km-grid / half-hour grain.

IMPORTANT — these are synthetic agents, not real trips. WorldMove simulates
~10-24k agents regardless of city size, so raw counts are NOT comparable across
cities or to NYC's real trip volumes. `worldmove_city.n_agents` and
`population_total` are stored so downstream can scale explicitly; no scaling is
baked in here.

    python scripts/load_worldmove_mobility.py
    python scripts/load_worldmove_mobility.py --self-check
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
POP_DIR = REPO_ROOT / "data" / "raw" / "worldmove_data"
TRAJ_DIR = REPO_ROOT / "data" / "raw" / "worldmove_traj"
GRID_DIR = REPO_ROOT / "data" / "raw" / "worldmove_grid"
DUCKDB_PATH = os.environ.get(
    "DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb")
)

FILENAME_RE = re.compile(r"^(\d+)_([A-Z]{2,3})_(.+)$")
SLOTS_PER_DAY = 48  # half-hourly


def parse_key(key: str) -> tuple[int, str, str] | None:
    match = FILENAME_RE.match(key)
    if not match:
        return None
    worldmove_id, country_code, city_slug = match.groups()
    return int(worldmove_id), country_code, city_slug.replace("_", " ")


def cell_activity(traj: np.ndarray, n_cells: int):
    """(departures, arrivals, occupancy) each shaped (n_cells, SLOTS_PER_DAY).

    Vectorised over agents; loops only over the 48 slots.
    """
    n_slots = traj.shape[1]
    departures = np.zeros((n_cells, n_slots), dtype=np.int64)
    arrivals = np.zeros((n_cells, n_slots), dtype=np.int64)
    occupancy = np.zeros((n_cells, n_slots), dtype=np.int64)

    for slot in range(n_slots):
        occupancy[:, slot] = np.bincount(traj[:, slot], minlength=n_cells)
        if slot + 1 >= n_slots:
            continue
        moved = traj[:, slot] != traj[:, slot + 1]
        if not moved.any():
            continue
        departures[:, slot] = np.bincount(traj[moved, slot], minlength=n_cells)
        arrivals[:, slot + 1] = np.bincount(traj[moved, slot + 1], minlength=n_cells)

    return departures, arrivals, occupancy


def cell_flows(traj: np.ndarray, n_cells: int):
    """(from_cell, to_cell, trips) over the whole day, movements only."""
    origins = traj[:, :-1].ravel()
    targets = traj[:, 1:].ravel()
    moved = origins != targets
    if not moved.any():
        return np.empty(0, np.int64), np.empty(0, np.int64), np.empty(0, np.int64)

    pair_key = origins[moved].astype(np.int64) * n_cells + targets[moved].astype(np.int64)
    unique_keys, counts = np.unique(pair_key, return_counts=True)
    return unique_keys // n_cells, unique_keys % n_cells, counts


def load_city(key: str):
    """Return (city_row, grid_rows, halfhour_rows, flow_rows) or None if incomplete."""
    parsed = parse_key(key)
    traj_path = TRAJ_DIR / f"{key}.npy"
    grid_path = GRID_DIR / f"{key}.json"
    pop_path = POP_DIR / f"{key}.npy"
    if parsed is None or not (grid_path.exists() and pop_path.exists()):
        return None

    worldmove_id, country_code, city_name = parsed
    population = np.load(pop_path)
    grid = json.loads(grid_path.read_text())
    # Trajectories are optional: grid + population alone already give a city its
    # real coordinates, which is what city resolution needs. A run before the
    # (much larger) trajectory download finishes still produces a usable
    # worldmove_city_grid; re-run after it lands to fill in the mobility tables.
    traj = np.load(traj_path) if traj_path.exists() else np.empty((0, SLOTS_PER_DAY), np.int64)

    n_rows, n_cols = population.shape
    n_cells = population.size
    if len(grid) != n_cells:
        raise ValueError(f"{key}: grid has {len(grid)} cells, population has {n_cells}")
    if traj.size and int(traj.max()) >= n_cells:
        raise ValueError(f"{key}: trajectory cell index {traj.max()} exceeds {n_cells} cells")

    cell_index = np.arange(n_cells, dtype=np.int32)
    coordinates = np.array([grid[str(i)] for i in range(n_cells)], dtype=np.float64)
    grid_frame = pd.DataFrame({
        "city_key": key,
        "worldmove_id": np.int32(worldmove_id),
        "cell_index": cell_index,
        "grid_row": (cell_index // n_cols).astype(np.int32),
        "grid_col": (cell_index % n_cols).astype(np.int32),
        "longitude": coordinates[:, 0],
        "latitude": coordinates[:, 1],
        # row-major flatten; verified against real coordinates by verify_grid_orientation()
        "population": population.ravel(),
    })

    departures, arrivals, occupancy = cell_activity(traj, n_cells)
    # keep only (cell, slot) pairs with something in them, so the table stays
    # proportional to real activity rather than to grid area
    active_cells, active_slots = np.nonzero(occupancy | departures | arrivals)
    halfhour_frame = pd.DataFrame({
        "city_key": key,
        "cell_index": active_cells.astype(np.int32),
        "slot": active_slots.astype(np.int32),
        "departures": departures[active_cells, active_slots],
        "arrivals": arrivals[active_cells, active_slots],
        "occupancy": occupancy[active_cells, active_slots],
    })

    origins, targets, trips = cell_flows(traj, n_cells)
    flow_frame = pd.DataFrame({
        "city_key": key,
        "from_cell": origins.astype(np.int32),
        "to_cell": targets.astype(np.int32),
        "trips": trips,
    })

    city_row = (
        key, worldmove_id, country_code, city_name,
        n_rows, n_cols, n_cells,
        int(traj.shape[0]), int(traj.shape[1]),
        float(population.sum()),
        int(trips.sum()) if len(trips) else 0,
    )
    return city_row, grid_frame, halfhour_frame, flow_frame


def verify_grid_orientation(key: str) -> str:
    """Check cell_index -> (row, col) really is row-major against real coordinates.

    Everything spatial (neighbour cells, centroid distance) depends on this, and
    a silently-transposed grid would still 'work' while being geographically wrong.
    """
    population = np.load(POP_DIR / f"{key}.npy")
    grid = json.loads((GRID_DIR / f"{key}.json").read_text())
    n_cols = population.shape[1]

    # within one row, column index should track longitude monotonically
    first_row = [grid[str(c)] for c in range(n_cols)]
    lons = [point[0] for point in first_row]
    lats = [point[1] for point in first_row]
    lon_monotonic = all(b > a for a, b in zip(lons, lons[1:]))
    lat_spread = max(lats) - min(lats)
    lon_spread = max(lons) - min(lons)
    return (f"{key}: row-major={'OK' if lon_monotonic else 'FAILED'} "
            f"(lon spread {lon_spread:.4f} vs lat spread {lat_spread:.4f} across one row)")


def self_check() -> None:
    """Hand-built trajectory with known answers."""
    # 3 agents, 4 slots, 2x2 grid (4 cells)
    traj = np.array([
        [0, 1, 1, 3],   # moves 0->1 at slot0, 1->3 at slot2
        [0, 0, 0, 0],   # never moves
        [2, 2, 3, 3],   # moves 2->3 at slot1
    ], dtype=np.int64)

    departures, arrivals, occupancy = cell_activity(traj, 4)
    assert occupancy[0, 0] == 2, occupancy[0, 0]          # agents 0 and 1 in cell 0
    assert occupancy[3, 3] == 2, occupancy[3, 3]          # agents 0 and 2 end in cell 3
    assert departures[0, 0] == 1, departures[0, 0]        # only agent 0 leaves cell 0
    assert arrivals[1, 1] == 1, arrivals[1, 1]
    assert departures[1, 2] == 1 and arrivals[3, 3] == 1
    assert departures.sum() == arrivals.sum() == 3        # exactly 3 movements total
    assert occupancy[:, 0].sum() == 3                     # every agent is somewhere

    origins, targets, trips = cell_flows(traj, 4)
    flows = {(int(a), int(b)): int(c) for a, b, c in zip(origins, targets, trips)}
    assert flows == {(0, 1): 1, (1, 3): 1, (2, 3): 1}, flows

    # a totally static city must produce no trips and no empty-cell rows
    static = np.zeros((5, 4), dtype=np.int64)
    dep, arr, occ = cell_activity(static, 4)
    assert dep.sum() == 0 and arr.sum() == 0 and occ[0, 0] == 5
    assert len(cell_flows(static, 4)[2]) == 0

    print("self-check OK")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if args.self_check:
        self_check()
        return

    # driven by the grid corpus, not trajectories -- see load_city() on why
    keys = sorted(p.stem for p in GRID_DIR.glob("*.json"))
    if args.limit:
        keys = keys[: args.limit]
    if not keys:
        raise SystemExit(f"no grids in {GRID_DIR} -- run download_worldmove.py --category grid")
    with_traj = sum(1 for k in keys if (TRAJ_DIR / f"{k}.npy").exists())
    print(f"{len(keys)} cities, {with_traj} with trajectories")

    print(verify_grid_orientation(keys[0]))

    con = duckdb.connect(DUCKDB_PATH)
    con.execute("""
        CREATE OR REPLACE TABLE worldmove_city (
            city_key VARCHAR PRIMARY KEY, worldmove_id INTEGER, country_code VARCHAR,
            city_name VARCHAR, grid_rows INTEGER, grid_cols INTEGER, grid_cells INTEGER,
            n_agents INTEGER, n_slots INTEGER, population_total DOUBLE, total_trips BIGINT
        )""")
    con.execute("""
        CREATE OR REPLACE TABLE worldmove_city_grid (
            city_key VARCHAR, worldmove_id INTEGER, cell_index INTEGER,
            grid_row INTEGER, grid_col INTEGER,
            longitude DOUBLE, latitude DOUBLE, population DOUBLE
        )""")
    con.execute("""
        CREATE OR REPLACE TABLE worldmove_cell_halfhour (
            city_key VARCHAR, cell_index INTEGER, slot INTEGER,
            departures BIGINT, arrivals BIGINT, occupancy BIGINT
        )""")
    con.execute("""
        CREATE OR REPLACE TABLE worldmove_cell_flows (
            city_key VARCHAR, from_cell INTEGER, to_cell INTEGER, trips BIGINT
        )""")

    totals = {"cities": 0, "grid": 0, "halfhour": 0, "flows": 0, "skipped": 0}
    city_rows: list[tuple] = []
    batches: dict[str, list[pd.DataFrame]] = {"grid": [], "halfhour": [], "flows": []}
    # DuckDB's executemany is row-at-a-time and unusably slow at these volumes;
    # registering a DataFrame and INSERT ... SELECT is a bulk columnar copy.
    table_for = {
        "grid": "worldmove_city_grid",
        "halfhour": "worldmove_cell_halfhour",
        "flows": "worldmove_cell_flows",
    }

    def flush() -> None:
        for name, frames in batches.items():
            if not frames:
                continue
            frame = pd.concat(frames, ignore_index=True)
            con.register("batch_frame", frame)
            con.execute(f"INSERT INTO {table_for[name]} SELECT * FROM batch_frame")
            con.unregister("batch_frame")
            frames.clear()

    for index, key in enumerate(keys, start=1):
        try:
            loaded = load_city(key)
        except ValueError as exc:
            print(f"SKIP {key}: {exc}", flush=True)
            totals["skipped"] += 1
            continue
        if loaded is None:
            totals["skipped"] += 1
            continue

        city_row, grid_frame, halfhour_frame, flow_frame = loaded
        city_rows.append(city_row)
        batches["grid"].append(grid_frame)
        batches["halfhour"].append(halfhour_frame)
        batches["flows"].append(flow_frame)

        totals["cities"] += 1
        totals["grid"] += len(grid_frame)
        totals["halfhour"] += len(halfhour_frame)
        totals["flows"] += len(flow_frame)
        if index % 25 == 0:
            flush()
            print(f"[{index}/{len(keys)}] {totals['cities']} cities, "
                  f"{totals['halfhour']:,} half-hour rows, {totals['flows']:,} flows", flush=True)

    flush()
    con.executemany("INSERT INTO worldmove_city VALUES (?,?,?,?,?,?,?,?,?,?,?)", city_rows)
    con.close()
    print(f"\nworldmove_city:          {totals['cities']:,} rows")
    print(f"worldmove_city_grid:     {totals['grid']:,} rows")
    print(f"worldmove_cell_halfhour: {totals['halfhour']:,} rows")
    print(f"worldmove_cell_flows:    {totals['flows']:,} rows")
    print(f"skipped (missing/invalid): {totals['skipped']}")


if __name__ == "__main__":
    main()
