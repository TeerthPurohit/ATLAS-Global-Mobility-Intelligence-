-- Generalizes the existing NYC zone dimension into the cross-city
-- (area_id, city_id, name, area_type, parent_area_id, latitude, longitude)
-- shape (SPEC-013 FR-3). Reads from the staging zone model plus the
-- zone_centroids seed -- never from a mart -- to respect rule 6 ("marts
-- don't read marts"). Grain: one row per NYC TLC zone plus one row per
-- London Santander Cycle Hire docking station -- a second city adds rows
-- here via its own staging model, no schema change needed.
--
-- London's station_id is a zero-padded VARCHAR terminal number
-- (stg_london_stations); cast to INTEGER so area_id stays a single type
-- across cities, matching every city-scoped API's `area_id: int` schema.

SELECT
    z.location_id AS area_id,
    'nyc'          AS city_id,
    z.zone_name    AS name,
    'zone'         AS area_type,
    z.borough      AS parent_area_id,
    c.latitude,
    c.longitude
FROM {{ ref('stg_zones') }} z
LEFT JOIN {{ ref('zone_centroids') }} c ON c.LocationID = z.location_id

UNION ALL

SELECT
    CAST(s.station_id AS INTEGER) AS area_id,
    'london'                      AS city_id,
    s.station_name                AS name,
    'station'                     AS area_type,
    NULL                          AS parent_area_id,
    s.latitude,
    s.longitude
FROM {{ ref('stg_london_stations') }} s
