-- Cleaned WorldMove city dimension. One row per city with a real trajectory
-- corpus (skips any city that only has a population grid -- see
-- scripts/load_worldmove_mobility.py, which requires grid+population but
-- makes trajectories optional so a partial download still loads coordinates).
--
-- Deliberately does NOT trust the filename-embedded country_code for
-- anything beyond a label: geocode_global_cities.py used it to constrain a
-- GeoNames name search and produced verifiably wrong locations (US_FALUN ->
-- Nevada; Falun is Swedish). This model's latitude/longitude instead come
-- straight from WorldMove's own grid coordinate file via
-- stg_worldmove_grid's population-weighted centroid -- no name-matching
-- guess involved.
SELECT
    c.city_key,
    -- Must match scripts/build_global_cities.py's _slug() exactly -- this is
    -- the city_id every backend registry/service joins on. Kept as one
    -- formula here rather than writing city_id from Python so dbt test can
    -- assert it's actually unique instead of trusting the generator.
    upper(c.country_code) || '_' ||
        trim(BOTH '_' FROM upper(regexp_replace(trim(c.city_name), '[^A-Za-z0-9]+', '_', 'g')))
        AS city_id,
    c.worldmove_id,
    c.country_code,
    c.city_name,
    c.grid_rows,
    c.grid_cols,
    c.grid_cells,
    c.n_agents,
    c.population_total,
    c.total_trips,
    -- a handful of cities WorldMove grids down to 1-4 cells; flag rather than
    -- silently treating a 1-cell "grid" the same as an 11,845-cell one
    c.grid_cells <= 4 AS is_coarse_grid
FROM {{ source('worldmove', 'worldmove_city') }} c
WHERE c.n_agents > 0
