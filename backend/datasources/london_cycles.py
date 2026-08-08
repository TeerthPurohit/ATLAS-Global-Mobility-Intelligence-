"""`LondonCyclesDataSource` -- mirrors `nyc_tlc.py`'s shape exactly, reading
London's own separately-attached warehouse (`london_cycles.duckdb`) instead
of NYC's. No fare mart or zone_pair_flows equivalent exists for London yet
(rule 2: honest empty lists, never a fabricated NYC-shaped stand-in).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "london_cycles.duckdb"


def _rows(sql: str, params: list) -> list[dict]:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        cur = con.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        con.close()


class LondonCyclesDataSource:
    city_id = "london"

    def get_areas(self) -> list[dict]:
        return _rows(
            "select area_id, city_id, name, area_type, parent_area_id, latitude, longitude "
            "from canonical_areas where city_id = ? order by area_id",
            [self.city_id],
        )

    def get_demand(
        self, area_id: int | None = None, hour: int | None = None, day_of_week: int | None = None
    ) -> list[dict]:
        clauses, params = [], []
        if area_id is not None:
            clauses.append("CAST(station_id AS INTEGER) = ?")
            params.append(area_id)
        if hour is not None:
            clauses.append("hour = ?")
            params.append(hour)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        return _rows(
            f"select trip_date, hour, station_id, station_name, total_trips "
            f"from london_station_hourly_demand {where} order by trip_date, hour",
            params,
        )

    def get_fares(self, pickup_area: str | None = None, dropoff_area: str | None = None) -> list[dict]:
        return []  # honest empty: no fare mart exists for London

    def get_zone_flows(self, pickup_area: str | None = None) -> list[dict]:
        return []  # honest empty: no zone_pair_flows equivalent exists for London

    def get_temporal_metrics(self, metric: str) -> list[dict]:
        if metric == "demand":
            return _rows(
                "select hour, sum(total_trips) as value "
                "from london_station_hourly_demand group by 1 order by 1",
                [],
            )
        raise KeyError(f"no temporal metric named {metric!r}")
