-- Per-grid-cell hour-of-day occupancy, real data from WorldMove trajectories.
-- This is the WorldMove-city analogue of what nyc/london's zone momentum
-- gives journey_predictors.py's _demand_pressure(): "how busy is this hour
-- at this specific area, relative to that area's own typical hour" -- the
-- signal availability/surge risk are built on. NYC/London compare
-- lag_1h to rolling_7d_avg (multi-day history); WorldMove has one
-- representative day (48 half-hour slots, no calendar, see
-- scripts/load_worldmove_mobility.py's module docstring), so the analogous
-- real ratio here is this hour's occupancy vs. this cell's own mean hourly
-- occupancy across that one day -- same shape of question, honestly scoped
-- to what a single-day trajectory can actually support.
WITH by_area_hour AS (
    SELECT
        g.area_id,
        g.city_id,
        h.slot // 2 AS hour,
        SUM(h.occupancy) AS occupancy
    FROM {{ source('worldmove', 'worldmove_cell_halfhour') }} h
    JOIN {{ ref('stg_worldmove_grid') }} g
        ON g.city_key = h.city_key AND g.cell_index = h.cell_index
    GROUP BY 1, 2, 3
),

area_daily_mean AS (
    SELECT area_id, AVG(occupancy) AS mean_hourly_occupancy
    FROM by_area_hour
    GROUP BY 1
)

SELECT
    by_area_hour.area_id,
    by_area_hour.city_id,
    by_area_hour.hour,
    by_area_hour.occupancy,
    area_daily_mean.mean_hourly_occupancy,
    CASE WHEN area_daily_mean.mean_hourly_occupancy > 0
         THEN by_area_hour.occupancy / area_daily_mean.mean_hourly_occupancy
         ELSE NULL END AS occupancy_ratio
FROM by_area_hour
JOIN area_daily_mean ON area_daily_mean.area_id = by_area_hour.area_id
