{{ config(database='london_cycles') }}
-- Grain: trips per docking station per real calendar date per hour
-- (SPEC-015) -- matches zone_hourly_demand's pickup_date/pickup_hour/
-- pickup_location_id grain (rule 3: chronological split needs a real date
-- column, not just day-of-week, so models/xgboost_model/split_demand_blocks()
-- can hold out the most recent month as a genuine future test set).
-- Column shape (station_id, trip_date, hour, day_of_week, total_trips,
-- avg_duration_min) deliberately mirrors zone_hourly_demand so existing
-- KD-tree/PageRank/EWMA algorithm code and demand-model training can
-- consume it with minimal adaptation. "Demand" here = bike-share
-- departures, not ride-hailing pickups.
WITH enriched AS (
    SELECT * FROM {{ ref('int_london_journeys_enriched') }}
)

SELECT
    start_station_id   AS station_id,
    start_station_name AS station_name,
    start_date          AS trip_date,
    start_hour          AS hour,
    start_day_of_week   AS day_of_week,

    COUNT(*)               AS total_trips,
    AVG(duration_minutes)  AS avg_duration_min

FROM enriched
GROUP BY 1, 2, 3, 4, 5
