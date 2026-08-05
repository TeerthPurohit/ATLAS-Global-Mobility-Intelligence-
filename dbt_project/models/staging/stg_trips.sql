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
