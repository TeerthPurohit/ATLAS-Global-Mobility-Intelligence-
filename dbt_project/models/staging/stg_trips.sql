WITH source AS (
    SELECT
        hvfhs_license_num,
        pickup_datetime,
        dropoff_datetime,
        PULocationID,
        DOLocationID,
        trip_miles,
        trip_time,
        base_passenger_fare,
        tolls,
        bcf,
        sales_tax,
        congestion_surcharge,
        airport_fee,
        tips,
        driver_pay
    FROM {{ source('nyc_tlc', 'raw_trips') }}
),

renamed AS (
    SELECT
        -- Primary key
        row_number() OVER () AS trip_id,

        -- Carrier (HV0002=Juno, HV0003=Uber, HV0004=Via, HV0005=Lyft)
        hvfhs_license_num,

        -- Timestamps
        pickup_datetime  AS pickup_at,
        dropoff_datetime AS dropoff_at,

        -- Location IDs
        PULocationID AS pickup_location_id,
        DOLocationID AS dropoff_location_id,

        -- Measured attributes
        trip_miles AS trip_distance,
        datediff('minute', pickup_datetime, dropoff_datetime) AS trip_duration_minutes,

        -- Fare breakdown (HVFHV has no fare_amount/tip_amount/total_amount — build them)
        base_passenger_fare AS fare_amount,
        tolls,
        bcf,
        sales_tax,
        congestion_surcharge,
        airport_fee,
        tips AS tip_amount,
        driver_pay

    FROM source
)

SELECT
    *,
    fare_amount + tolls + bcf + sales_tax + congestion_surcharge + airport_fee + tip_amount AS total_amount
FROM renamed
-- drop clearly broken rows: comped/refunded trips (<=0) and implausible outlier fares (>=$1000)
WHERE fare_amount + tolls + bcf + sales_tax + congestion_surcharge + airport_fee + tip_amount > 0
  AND fare_amount + tolls + bcf + sales_tax + congestion_surcharge + airport_fee + tip_amount < 1000
  -- drop physically-impossible trips: negative wall-clock duration (12,203 of 113M rows measured)
  AND dropoff_at >= pickup_at
  -- drop implausible implied speed (trip_distance / duration_hours); observed p99=37mph,
  -- p999=47mph, p9999=74mph, p99999=121mph, max=4646.8mph -- 80mph matches the plausibility
  -- bound already used by models/congestion/build_features.py's build_free_flow_lookup() for
  -- consistency, and only excludes 256 of 113M rows (the true GPS/meter-error tail, not the
  -- long-but-plausible highway trips e.g. a 350-mile trip at ~55mph passes this bound).
  -- Rows with trip_duration_minutes <= 0 are left to the null-speed downstream handling
  -- (not this project's flagged defect) rather than divided-by-zero here.
  AND (trip_duration_minutes <= 0 OR trip_distance / (trip_duration_minutes / 60.0) <= 80)
