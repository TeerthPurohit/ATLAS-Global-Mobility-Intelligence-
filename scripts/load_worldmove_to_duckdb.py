"""Load WorldMove population-mobility grids (data/raw/worldmove_data/*.npy)
into nyc_rides.duckdb as worldmove_city_population -- one row per city,
summarizing each city's grid rather than storing the raw array (nothing
downstream needs cell-level resolution; global_geography_service only needs
a population/mobility-intensity signal per city, same shape as the
population covariate resolve_modeling_availability() already checks).

Filename convention (from scripts/download_worldmove_india.py):
`{worldmove_id}_{country_code}_{city_name}.npy`, city_name with underscores
for spaces.
"""
import os
import re
from pathlib import Path

import duckdb
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "worldmove_data"
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"))

FILENAME_RE = re.compile(r"^(\d+)_([A-Z]{2,3})_(.+)\.npy$")


def parse_rows():
    rows = []
    for path in sorted(RAW_DIR.glob("*.npy")):
        m = FILENAME_RE.match(path.name)
        if not m:
            continue  # skip non-matching files (e.g. a stray index.html)
        worldmove_id, country_code, city_slug = m.groups()
        grid = np.load(path, allow_pickle=True)
        rows.append((
            int(worldmove_id),
            country_code,
            city_slug.replace("_", " "),
            grid.shape[0],
            grid.shape[1],
            float(grid.sum()),
            float(grid.mean()),
            float(grid.max()),
            path.name,
        ))
    return rows


def main():
    rows = parse_rows()
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("""
        CREATE OR REPLACE TABLE worldmove_city_population (
            worldmove_id INTEGER PRIMARY KEY,
            country_code VARCHAR,
            city_name VARCHAR,
            grid_rows INTEGER,
            grid_cols INTEGER,
            population_total DOUBLE,
            population_density_mean DOUBLE,
            population_density_max DOUBLE,
            source_file VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO worldmove_city_population VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    n = con.execute("SELECT count(*) FROM worldmove_city_population").fetchone()[0]
    print(f"worldmove_city_population: {n:,} rows loaded")
    con.close()


if __name__ == "__main__":
    main()
