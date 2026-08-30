"""The one real CityMobilitySchema, for NYC's actual marts (FR-3).

Column/table names verified against the current mart SQL, not the spec's
paraphrase -- two corrections worth flagging:

- `day_of_week` is computed in `int_trips_enriched` (`pickup_day_of_week`)
  but is not selected into any of the three marts `sql_agent.py` is allowed
  to read (`zone_hourly_demand`, `zone_fare_stats`, `zone_pair_flows`), so it
  is not resolvable for NYC at all today -- omitted from every metric below
  rather than pointing at a column that doesn't exist.
- `area` does not resolve to one column: `zone_hourly_demand` carries
  `pickup_location_id` (a numeric zone id), but `zone_fare_stats` and
  `zone_pair_flows` have no location-id column at all, only `pickup_zone`
  (a text zone name). Each metric below maps `area` to whichever column its
  own table actually has.
- `zone_fare_stats` and `zone_pair_flows` also have no hour column; `hour`
  is only resolvable for the `demand` metric.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from query_plan import CityMobilitySchema, FieldMapping, MetricSchema

NYC_SCHEMA = CityMobilitySchema(
    name="nyc",
    metrics={
        "demand": MetricSchema(
            table="zone_hourly_demand",
            value=FieldMapping("total_trips", "count of trips picked up"),
            filters={
                "area": FieldMapping("pickup_location_id", "pickup zone id", is_text=False),
                "borough": FieldMapping("pickup_borough", "pickup borough name", is_text=True),
                "hour": FieldMapping("pickup_hour", "hour of day pickup occurred, 0-23"),
                "date_range": FieldMapping("pickup_date", "pickup calendar date"),
            },
        ),
        "fare": MetricSchema(
            table="zone_fare_stats",
            value=FieldMapping("avg_fare", "average fare amount"),
            filters={
                "area": FieldMapping("pickup_zone", "pickup zone name", is_text=True),
                "borough": FieldMapping("pickup_borough", "pickup borough name", is_text=True),
                "dest_area": FieldMapping("dropoff_zone", "dropoff zone name", is_text=True),
                "dest_borough": FieldMapping("dropoff_borough", "dropoff borough name", is_text=True),
            },
        ),
        "distance": MetricSchema(
            table="zone_fare_stats",
            value=FieldMapping("avg_distance", "average trip distance in miles"),
            filters={
                "area": FieldMapping("pickup_zone", "pickup zone name", is_text=True),
                "borough": FieldMapping("pickup_borough", "pickup borough name", is_text=True),
                "dest_area": FieldMapping("dropoff_zone", "dropoff zone name", is_text=True),
                "dest_borough": FieldMapping("dropoff_borough", "dropoff borough name", is_text=True),
            },
        ),
        "duration": MetricSchema(
            table="zone_fare_stats",
            value=FieldMapping("avg_duration_min", "average trip duration in minutes"),
            filters={
                "area": FieldMapping("pickup_zone", "pickup zone name", is_text=True),
                "borough": FieldMapping("pickup_borough", "pickup borough name", is_text=True),
                "dest_area": FieldMapping("dropoff_zone", "dropoff zone name", is_text=True),
                "dest_borough": FieldMapping("dropoff_borough", "dropoff borough name", is_text=True),
            },
        ),
        "speed": MetricSchema(
            table="zone_pair_flows",
            value=FieldMapping("avg_speed_mph", "average speed in miles per hour"),
            filters={
                "area": FieldMapping("pickup_zone", "pickup zone name", is_text=True),
                "borough": FieldMapping("pickup_borough", "pickup borough name", is_text=True),
                "dest_area": FieldMapping("dropoff_zone", "dropoff zone name", is_text=True),
                "dest_borough": FieldMapping("dropoff_borough", "dropoff borough name", is_text=True),
                "date_range": FieldMapping("pickup_date", "pickup calendar date"),
            },
        ),
        "flow": MetricSchema(
            table="zone_pair_flows",
            value=FieldMapping("trip_count", "count of trips between a pickup/dropoff zone pair"),
            filters={
                "area": FieldMapping("pickup_zone", "pickup zone name", is_text=True),
                "borough": FieldMapping("pickup_borough", "pickup borough name", is_text=True),
                "dest_area": FieldMapping("dropoff_zone", "dropoff zone name", is_text=True),
                "dest_borough": FieldMapping("dropoff_borough", "dropoff borough name", is_text=True),
                "date_range": FieldMapping("pickup_date", "pickup calendar date"),
            },
        ),
    },
)


def demo() -> None:
    text = NYC_SCHEMA.describe()
    assert "TABLE zone_hourly_demand" in text
    assert "TABLE zone_fare_stats" in text
    assert "TABLE zone_pair_flows" in text
    assert not NYC_SCHEMA.has_field("fare", "hour"), "zone_fare_stats has no hour column"
    assert not NYC_SCHEMA.has_field("demand", "day_of_week"), "no mart exposes day_of_week today"
    print(text)
    print("\nOK: NYC_SCHEMA resolves only columns that actually exist in the marts")


if __name__ == "__main__":
    demo()
