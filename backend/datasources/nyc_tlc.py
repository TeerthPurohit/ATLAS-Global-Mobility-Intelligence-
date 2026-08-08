"""`NYCTLCDataSource` (SPEC-013 FR-6) -- thin read wrappers over the existing
NYC marts, via the same per-call read-only DuckDB connection pattern
`model_service.py`/`platform_service.py` already use. Every query here reads
a pre-aggregated mart (`canonical_areas`, `zone_hourly_demand`,
`zone_fare_stats`, `zone_pair_flows`), never a raw table (rule 8).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"


def _rows(sql: str, params: list) -> list[dict]:
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        cur = con.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        con.close()


class NYCTLCDataSource:
    city_id = "nyc"

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
            clauses.append("pickup_location_id = ?")
            params.append(area_id)
        if hour is not None:
            clauses.append("pickup_hour = ?")
            params.append(hour)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        return _rows(
            f"select pickup_date, pickup_hour, pickup_location_id, pickup_zone, total_trips, avg_fare "
            f"from zone_hourly_demand {where} order by pickup_date, pickup_hour",
            params,
        )

    def get_fares(self, pickup_area: str | None = None, dropoff_area: str | None = None) -> list[dict]:
        clauses, params = [], []
        if pickup_area is not None:
            clauses.append("pickup_zone = ?")
            params.append(pickup_area)
        if dropoff_area is not None:
            clauses.append("dropoff_zone = ?")
            params.append(dropoff_area)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        return _rows(
            f"select pickup_zone, dropoff_zone, trip_count, avg_fare, median_fare, min_fare, max_fare "
            f"from zone_fare_stats {where}",
            params,
        )

    def get_zone_flows(self, pickup_area: str | None = None) -> list[dict]:
        clauses, params = [], []
        if pickup_area is not None:
            clauses.append("pickup_zone = ?")
            params.append(pickup_area)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        return _rows(
            f"select pickup_date, pickup_zone, dropoff_zone, trip_count, avg_duration_min, avg_speed_mph "
            f"from zone_pair_flows {where} order by pickup_date, trip_count desc",
            params,
        )

    def get_temporal_metrics(self, metric: str) -> list[dict]:
        if metric == "demand":
            return _rows(
                "select pickup_hour as hour, sum(total_trips) as value "
                "from zone_hourly_demand group by 1 order by 1",
                [],
            )
        if metric == "fare":
            return _rows(
                "select pickup_hour as hour, sum(avg_fare * total_trips) / nullif(sum(total_trips), 0) as value "
                "from zone_hourly_demand group by 1 order by 1",
                [],
            )
        raise KeyError(f"no temporal metric named {metric!r}")
