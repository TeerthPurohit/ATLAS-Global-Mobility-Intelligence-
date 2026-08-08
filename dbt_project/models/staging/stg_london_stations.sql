{{ config(database='london_cycles') }}
-- Casts/renames only (rule 6). Source: dbt seed dbt_project/seeds/london_stations.csv,
-- itself a direct dump of TfL's live BikePoint API (station_id == the same
-- zero-padded docking-station terminal number used in the journey extracts).
SELECT
    station_id,
    name AS station_name,
    latitude,
    longitude
FROM {{ ref('london_stations') }}
