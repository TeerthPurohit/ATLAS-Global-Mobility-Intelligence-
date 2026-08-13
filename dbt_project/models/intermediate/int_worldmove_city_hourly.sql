-- Half-hour slots (0-47) collapsed to hour-of-day (0-23) departures, summed
-- across every grid cell in a city. This is a same-city aggregate, not
-- per-area -- worldmove_cell_halfhour / stg_worldmove_grid still carry the
-- per-cell detail for anything that later needs area-level demand.
SELECT
    c.city_id,
    h.city_key,
    h.slot // 2 AS hour,  -- integer division: DuckDB's `/` is float and would leave slot 47 as 23.5
    SUM(h.departures) AS total_departures
FROM {{ source('worldmove', 'worldmove_cell_halfhour') }} h
JOIN {{ ref('stg_worldmove_cities') }} c ON c.city_key = h.city_key
GROUP BY 1, 2, 3
