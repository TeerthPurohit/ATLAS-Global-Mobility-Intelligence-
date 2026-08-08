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
),

-- City-level weather only (never per-station -- see zone_hourly_demand.sql's
-- identical note; weather doesn't meaningfully vary within one city).
weather AS (
    SELECT date, hour, temperature_c, precipitation_mm
    FROM {{ ref('weather_hourly') }}
    WHERE city_id = 'london'
)

SELECT
    enriched.start_station_id   AS station_id,
    enriched.start_station_name AS station_name,
    enriched.start_date          AS trip_date,
    enriched.start_hour          AS hour,
    enriched.start_day_of_week   AS day_of_week,

    COUNT(*)                    AS total_trips,
    AVG(enriched.duration_minutes) AS avg_duration_min,
    MAX(weather.temperature_c)     AS temperature_c,
    MAX(weather.precipitation_mm)  AS precipitation_mm

FROM enriched
LEFT JOIN weather ON weather.date = enriched.start_date AND weather.hour = enriched.start_hour
GROUP BY 1, 2, 3, 4, 5
