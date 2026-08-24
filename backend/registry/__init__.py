"""Registry package.

`CITY_ID` lives here rather than in `registry/cities.py` so that any module
can import it without an import cycle (`cities` already imports `models` and
`transit`). It is the one place "nyc" is spelled out on the serving path:
after ADR-013 nothing passes a city id around, but the tables underneath
still carry one, and this is what they are filtered by. Adding a second city
means finding every use of this constant and deciding which should become a
parameter again.
"""

CITY_ID = "nyc"
