{{ config(database='london_cycles') }}
-- Casts/renames only (rule 6) -- no joins, no derived business columns.
-- Source: TfL Santander Cycle Hire journey extracts (bike-share, not
-- ride-hailing -- see scripts/ingest_tfl_cycle_hire.py for provenance).
WITH source AS (
    SELECT
        "Number"                AS journey_id,
        "Start date"             AS start_at,
        "Start station number"   AS start_station_id,
        "End date"               AS end_at,
        "End station number"     AS end_station_id,
        "Bike number"            AS bike_id,
        "Bike model"             AS bike_model,
        "Total duration (ms)"    AS duration_ms
    FROM {{ source('tfl_cycling', 'raw_journeys') }}
)

SELECT
    journey_id,
    start_at,
    end_at,
    start_station_id,
    end_station_id,
    bike_id,
    bike_model,
    duration_ms / 60000.0 AS duration_minutes
FROM source
-- drop obviously-broken rows: TfL's own extracts carry a small number of
-- legacy duplicate terminal ids (e.g. "0010684444" for a station literally
-- named "..._OLD" in the same row) that are 10 digits instead of every real
-- BikePoint terminal's 6 -- ~0.05% of rows, a malformed id, not a business
-- rule.
WHERE LENGTH(start_station_id) = 6
  AND LENGTH(end_station_id) = 6
