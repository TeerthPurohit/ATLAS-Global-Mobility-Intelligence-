-- Assert that no recorded trip has a non-positive fare amount
SELECT
    trip_id,
    total_amount
FROM {{ ref('stg_trips') }}
WHERE total_amount <= 0
