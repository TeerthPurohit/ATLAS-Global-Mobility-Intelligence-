WITH enriched AS (
    SELECT * FROM {{ ref('int_trips_enriched') }}
)

SELECT
    pickup_date,
    pickup_hour,
    pickup_location_id,
    pickup_borough,
    pickup_zone,

    COUNT(*)           AS total_trips,
    SUM(passenger_count) AS total_passengers,
    AVG(trip_distance) AS avg_trip_distance_miles,
    AVG(total_amount)  AS avg_fare

FROM enriched
GROUP BY 1, 2, 3, 4, 5
