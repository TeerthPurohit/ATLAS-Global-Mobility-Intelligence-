-- Generalizes the existing NYC zone dimension into the cross-city
-- (area_id, city_id, name, area_type, parent_area_id, latitude, longitude)
-- shape (SPEC-013 FR-3). Reads from the staging zone model plus the
-- zone_centroids seed -- never from a mart -- to respect rule 6 ("marts
-- don't read marts"). Grain: one row per NYC TLC zone today; a second
-- city adds rows here via its own staging model, no schema change needed.

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
