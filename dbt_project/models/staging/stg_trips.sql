WITH source AS (
    SELECT
        VendorID,
        tpep_pickup_datetime,
        tpep_dropoff_datetime,
        passenger_count,
        trip_distance,
        RatecodeID,
        store_and_fwd_flag,
        PULocationID,
        DOLocationID,
        payment_type,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        congestion_surcharge,
        AirportFee
    FROM {{ source('nyc_tlc', 'yellow_tripdata') }}
)

SELECT
    -- Primary key
    row_number() OVER () AS trip_id,

    -- Vendor
    VendorID AS vendor_id,

    -- Timestamps
    tpep_pickup_datetime AS pickup_at,
    tpep_dropoff_datetime AS dropoff_at,

    -- Measured attributes
    passenger_count,
    trip_distance,

    -- Location IDs
    PULocationID AS pickup_location_id,
    DOLocationID AS dropoff_location_id,

    -- Rate / payment
    RatecodeID AS rate_code_id,
    payment_type,

    -- Fare breakdown
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    total_amount,

    -- Computed helpers
    datediff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) AS trip_duration_minutes,

    -- Flags
    CASE WHEN total_amount > 0 THEN TRUE ELSE FALSE END AS is_valid_fare

FROM source
