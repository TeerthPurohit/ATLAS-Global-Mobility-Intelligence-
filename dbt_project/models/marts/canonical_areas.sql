-- The NYC zone dimension in the (area_id, name, area_type,
-- parent_area_id, latitude, longitude) shape the area APIs read.
-- Reads from the staging zone model plus the zone_centroids seed -- never
-- from a mart -- to respect rule 6 ("marts don't read marts").
-- Grain: one row per NYC TLC zone.
--
-- The constant `city_id` column ADR-012 kept is gone (ADR-013): with one
-- city it carried no information, and nothing above this reads it.

SELECT
    z.location_id AS area_id,
    z.zone_name    AS name,
    'zone'         AS area_type,
    z.borough      AS parent_area_id,
    c.latitude,
    c.longitude
FROM {{ ref('stg_zones') }} z
LEFT JOIN {{ ref('zone_centroids') }} c ON c.LocationID = z.location_id
