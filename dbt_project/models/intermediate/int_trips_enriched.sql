WITH trips AS (
    SELECT * FROM {{ ref('stg_trips') }}
),

zones AS (
    SELECT * FROM {{ ref('stg_zones') }}
)

SELECT
    trips.*,

    -- Pickup zone info
    pickup.borough    AS pickup_borough,
    pickup.zone_name  AS pickup_zone,
    pickup.service_zone AS pickup_service_zone,

    -- Dropoff zone info
    dropoff.borough   AS dropoff_borough,
    dropoff.zone_name AS dropoff_zone,
    dropoff.service_zone AS dropoff_service_zone,

    -- Speed (miles per hour)
    CASE
        WHEN trip_duration_minutes > 0
            THEN trip_distance / (trip_duration_minutes / 60.0)
        ELSE NULL
    END AS avg_speed_mph,

    -- Time dimensions
    extract('hour' FROM pickup_at)     AS pickup_hour,
    extract('dow'  FROM pickup_at)     AS pickup_day_of_week,
    extract('month' FROM pickup_at)    AS pickup_month,
    CAST(pickup_at AS DATE)            AS pickup_date

FROM trips
LEFT JOIN zones AS pickup  ON trips.pickup_location_id  = pickup.location_id
LEFT JOIN zones AS dropoff ON trips.dropoff_location_id = dropoff.location_id
