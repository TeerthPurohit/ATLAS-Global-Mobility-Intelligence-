WITH enriched AS (
    SELECT * FROM {{ ref('int_trips_enriched') }}
),

-- City-level weather only (never per-zone -- weather doesn't meaningfully
-- vary across one city's zones, so per-zone precision would be fake).
weather AS (
    SELECT date, hour, temperature_c, precipitation_mm
    FROM {{ ref('weather_hourly') }}
    WHERE city_id = 'nyc'
)

SELECT
    enriched.pickup_date,
    enriched.pickup_hour,
    enriched.pickup_location_id,
    enriched.pickup_borough,
    enriched.pickup_zone,

    COUNT(*)                   AS total_trips,
    AVG(enriched.trip_distance) AS avg_trip_distance_miles,
    AVG(enriched.total_amount)  AS avg_fare,
    -- MAX() is a determinism device, not an aggregation choice -- the join
    -- key is already unique per (date, hour), every row in the group shares
    -- one weather value; MAX just satisfies GROUP BY without adding weather
    -- to the grain.
    MAX(weather.temperature_c)   AS temperature_c,
    MAX(weather.precipitation_mm) AS precipitation_mm

FROM enriched
LEFT JOIN weather ON weather.date = enriched.pickup_date AND weather.hour = enriched.pickup_hour
GROUP BY 1, 2, 3, 4, 5
