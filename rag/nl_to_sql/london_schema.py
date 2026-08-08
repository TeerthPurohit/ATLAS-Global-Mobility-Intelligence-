"""London's real CityMobilitySchema -- demand (bike-share departures) only.
No fare/flow mart exists for London (see backend/datasources/london_cycles.py's
honest empty get_fares()/get_zone_flows()), so those metrics are simply
absent here rather than pointing at columns that don't exist.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from query_plan import CityMobilitySchema, FieldMapping, MetricSchema  # noqa: E402

LONDON_SCHEMA = CityMobilitySchema(
    name="london",
    metrics={
        "demand": MetricSchema(
            table="london_station_hourly_demand",
            value=FieldMapping("total_trips", "count of bike-share departures"),
            filters={
                "area": FieldMapping("station_id", "docking station id", is_text=True),
                "hour": FieldMapping("hour", "hour of day departure occurred, 0-23"),
                "date_range": FieldMapping("trip_date", "departure calendar date"),
            },
        ),
    },
)


def demo() -> None:
    text = LONDON_SCHEMA.describe()
    assert "TABLE london_station_hourly_demand" in text
    assert LONDON_SCHEMA.has_field("demand", "hour")
    assert not LONDON_SCHEMA.has_field("fare", "area"), "no fare mart exists for London"
    print(text)
    print("\nOK: LONDON_SCHEMA resolves only columns that actually exist in the marts")


if __name__ == "__main__":
    demo()
