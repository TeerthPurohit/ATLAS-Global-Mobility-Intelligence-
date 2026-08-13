-- Real per-city hour-of-day demand shape for every WorldMove city, computed
-- from that city's own simulated departures -- NOT NYC's shape. This is the
-- mart that closes the estimation_service.py bug where
-- hourly_shape_fraction(..., city_id="nyc") was applied to all 521
-- non-NYC/London cities regardless of the requested city.
--
-- Grain: (city_id, hour, day_of_week, pct_of_daily_trips). WorldMove only
-- simulates one representative day per city (48 half-hour slots, no
-- calendar) -- there is no real day-of-week signal to derive, so the same
-- day's shape is repeated across all 7 day_of_week values rather than
-- inventing weekly variation that doesn't exist in the source data. This
-- mirrors zone_hourly_demand/london_station_hourly_demand's
-- (hour, day_of_week) -> total_trips shape that
-- backend/services/model_service.py already builds `_hourly_shape` from,
-- just for a city with a single-day source instead of a multi-month one.
WITH by_hour AS (
    SELECT city_id, hour, total_departures
    FROM {{ ref('int_worldmove_city_hourly') }}
),

daily_total AS (
    SELECT city_id, SUM(total_departures) AS city_total
    FROM by_hour
    GROUP BY 1
),

day_of_week AS (
    -- 0-6, cross joined so every city gets a full week even though the
    -- underlying shape doesn't vary by day (see model note above)
    SELECT unnest(generate_series(0, 6)) AS day_of_week
)

SELECT
    by_hour.city_id,
    by_hour.hour,
    day_of_week.day_of_week,
    by_hour.total_departures,
    daily_total.city_total,
    CASE WHEN daily_total.city_total > 0
         THEN by_hour.total_departures::DOUBLE / daily_total.city_total
         ELSE NULL END AS pct_of_daily_trips
FROM by_hour
JOIN daily_total ON daily_total.city_id = by_hour.city_id
CROSS JOIN day_of_week
