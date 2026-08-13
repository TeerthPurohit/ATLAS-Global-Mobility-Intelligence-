"""RAG layer: the non-trivial, LLM-independent logic gets a real test
(standards.md) -- the grounding validator, session store, and NL-to-SQL security guard
are both branch-heavy parsing logic where a silent regression would be
exactly the failure mode this project exists to avoid.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "insight_generation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "nl_to_sql"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag" / "router"))

from generate_insight_docs import validate_grounding  # noqa: E402
from query_classifier import _heuristic_classify, EXPLANATORY, NUMERIC  # noqa: E402
import session_store  # noqa: E402
from sql_agent import _validate_sql  # noqa: E402


# ---- generate_insight_docs.validate_grounding ----

def test_validate_grounding_accepts_grounded_numbers():
    text = "This zone recorded 23435 trips, busiest at 08:00 with 1748 trips (7.5% share)."
    allowed = {23435.0, 1748.0, 7.5}
    assert validate_grounding(text, allowed)


def test_validate_grounding_rejects_invented_number():
    text = "This zone recorded 23435 trips, roughly 50000 more than its neighbor."
    allowed = {23435.0}
    assert not validate_grounding(text, allowed)


def test_validate_grounding_allows_small_connective_numbers():
    # hour-of-day / month counts never need a citation -- see _LOOSE_NUMBER_MAX
    text = "Busiest around 18:00, based on 3 months of data."
    assert validate_grounding(text, allowed=set())


# ---- sql_agent security guard ----

@pytest.mark.parametrize(
    "bad_sql",
    [
        "SELECT * FROM stg_trips",
        "SELECT * FROM int_trips_enriched",
        "DROP TABLE zone_hourly_demand",
        "SELECT * FROM zone_hourly_demand; DROP TABLE zone_hourly_demand",
        "INSERT INTO zone_hourly_demand VALUES (1)",
        "PRAGMA table_info(zone_hourly_demand)",
    ],
)
def test_sql_agent_rejects_disallowed_sql(bad_sql):
    with pytest.raises(ValueError):
        _validate_sql(bad_sql)


def test_sql_agent_accepts_wellformed_mart_query():
    good = (
        "WITH by_zone AS (SELECT pickup_zone, AVG(avg_fare) AS avg_fare FROM zone_hourly_demand GROUP BY 1) "
        "SELECT * FROM by_zone WHERE pickup_zone = 'JFK Airport'"
    )
    _validate_sql(good)  # must not raise


# ---- query_classifier heuristic fallback (no LLM call) ----

def test_heuristic_classify_numeric():
    assert _heuristic_classify("What's the average fare from Zone 161 to JFK?") == NUMERIC


def test_heuristic_classify_explanatory():
    assert _heuristic_classify("Why does Zone 161 get busy at rush hour?") == EXPLANATORY


def test_heuristic_classify_ambiguous_defaults_numeric():
    # ADR-004: SQL beats LLM reasoning in the precedence order -- an
    # ambiguous question should route to NL-to-SQL first, not explanation.
    assert _heuristic_classify("Tell me about Zone 161") == NUMERIC


# ---- session_store Postgres conversation persistence ----
# Needs a real DATABASE_URL (RDS or any Postgres) -- skipped otherwise since
# there's no local Postgres fixture in this repo (ADR-009).

@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_session_store_crud():
    table_name = f"test_messages_{uuid.uuid4().hex[:8]}"
    session_id = "test-session-123"
    try:
        assert not session_store.session_exists(session_id, table_name=table_name)

        session_store.save_message(session_id, "user", "Hello", table_name=table_name)
        session_store.save_message(session_id, "assistant", "Hi there", route="numeric", sql="SELECT 1", table_name=table_name)

        assert session_store.session_exists(session_id, table_name=table_name)

        history = session_store.get_session_history(session_id, table_name=table_name)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["route"] == "numeric"
        assert history[1]["sql"] == "SELECT 1"
    finally:
        with session_store.get_connection() as conn:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
