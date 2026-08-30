"""Phase 4 semantic-cache hit-rate tests -- pure counter logic, no live
Qdrant needed (get()/put() themselves already require one, matching every
other Qdrant-dependent module in this repo, which is exercised via its own
demo() rather than pytest).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

import semantic_cache


def _reset_counters():
    semantic_cache._HITS = 0
    semantic_cache._MISSES = 0


def test_hit_rate_none_when_no_lookups_yet():
    _reset_counters()
    assert semantic_cache.get_stats() == {"hits": 0, "misses": 0, "hit_rate": None}


def test_hit_rate_computed_from_recorded_hits_and_misses():
    _reset_counters()
    semantic_cache._record_hit()
    semantic_cache._record_hit()
    semantic_cache._record_hit()
    semantic_cache._record_miss()

    stats = semantic_cache.get_stats()
    assert stats == {"hits": 3, "misses": 1, "hit_rate": 0.75}


def test_all_misses_gives_zero_hit_rate_not_none():
    _reset_counters()
    semantic_cache._record_miss()
    semantic_cache._record_miss()

    stats = semantic_cache.get_stats()
    assert stats["hit_rate"] == 0.0
