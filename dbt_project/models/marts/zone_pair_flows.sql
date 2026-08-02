WITH enriched AS (
    SELECT * FROM {{ ref('int_trips_enriched') }}
),

flows AS (
    SELECT
        pickup_date,
        pickup_borough,
        pickup_zone,
        dropoff_borough,
        dropoff_zone,

        COUNT(*)              AS trip_count,
        SUM(total_amount)     AS total_revenue,
        AVG(trip_duration_minutes) AS avg_duration_min

    FROM enriched
    GROUP BY 1, 2, 3, 4, 5
)

SELECT
    *,
    ROW_NUMBER() OVER (
        PARTITION BY pickup_date, pickup_borough, pickup_zone
        ORDER BY trip_count DESC
    ) AS flow_rank
FROM flows
