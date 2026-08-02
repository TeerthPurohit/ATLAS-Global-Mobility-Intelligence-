SELECT
    LocationID AS location_id,
    Borough      AS borough,
    Zone         AS zone_name,
    service_zone AS service_zone
FROM {{ ref('taxi_zone_lookup') }}
