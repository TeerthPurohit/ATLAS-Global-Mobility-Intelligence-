WITH enriched AS (
    SELECT * FROM {{ ref('int_trips_enriched') }}
)

SELECT
    pickup_borough,
    pickup_zone,
    dropoff_borough,
    dropoff_zone,

    COUNT(*)              AS trip_count,
    AVG(fare_amount)      AS avg_fare,
    PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY fare_amount) AS median_fare,
    MIN(fare_amount)      AS min_fare,
    MAX(fare_amount)      AS max_fare,
    AVG(tip_amount)       AS avg_tip,
    AVG(trip_distance)    AS avg_distance,
    AVG(trip_duration_minutes) AS avg_duration_min

FROM enriched
GROUP BY 1, 2, 3, 4
