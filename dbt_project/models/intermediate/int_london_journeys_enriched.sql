{{ config(database='london_cycles') }}
-- Joins + derived columns (rule 6) -- mirrors int_trips_enriched's role:
-- station metadata joins, time-dimension extraction, and the one outlier
-- filter this dataset needs.
WITH journeys AS (
    SELECT * FROM {{ ref('stg_london_cycle_journeys') }}
),

stations AS (
    SELECT * FROM {{ ref('stg_london_stations') }}
)

SELECT
    journeys.*,

    -- Start station info
    start_station.station_name AS start_station_name,
    start_station.latitude     AS start_station_lat,
    start_station.longitude    AS start_station_lon,

    -- End station info
    end_station.station_name   AS end_station_name,
    end_station.latitude       AS end_station_lat,
    end_station.longitude      AS end_station_lon,

    -- Time dimensions
    extract('hour' FROM start_at)          AS start_hour,
    extract('dow'  FROM start_at)          AS start_day_of_week,
    CAST(start_at AS DATE)                 AS start_date,
    extract('dow' FROM start_at) IN (0, 6) AS is_weekend

FROM journeys
LEFT JOIN stations AS start_station ON journeys.start_station_id = start_station.station_id
LEFT JOIN stations AS end_station   ON journeys.end_station_id   = end_station.station_id
-- Drop obviously-broken rows: <=0 min (failed unlock / clock skew) and
-- >24h (TfL's Santander Cycles "return within 24 hours or be charged for a
-- lost bike" policy -- a checkout still open past 24h is a lost/stolen-bike
-- incident, not a real trip). Mirrors int_trips_enriched's 0 < total_fare <
-- 1000 outlier filter.
WHERE duration_minutes > 0
  AND duration_minutes <= 1440
