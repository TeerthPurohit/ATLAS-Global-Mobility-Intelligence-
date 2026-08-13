-- One row per WorldMove grid cell, with a globally-unique integer area_id so
-- these cells can sit in canonical_areas alongside NYC zones (1-265) and
-- London stations (max observed 300253) with no collision.
--
-- Offset scheme: 9,000,000 + worldmove_id * 20,000 + cell_index. The largest
-- observed grid is 11,845 cells and the largest worldmove_id is 1,131, so
-- 20,000 leaves headroom and the whole range (max ~31.6M) fits a 32-bit
-- INTEGER with room to spare -- verified against the live corpus, not a
-- guessed constant.
SELECT
    9000000 + g.worldmove_id * 20000 + g.cell_index AS area_id,
    c.city_id,
    g.city_key,
    g.worldmove_id,
    g.cell_index,
    g.grid_row,
    g.grid_col,
    g.longitude,
    g.latitude,
    g.population
FROM {{ source('worldmove', 'worldmove_city_grid') }} g
JOIN {{ ref('stg_worldmove_cities') }} c ON c.city_key = g.city_key
