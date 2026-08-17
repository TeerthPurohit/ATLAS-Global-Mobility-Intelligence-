"""Semantic answer cache shared by rag_pipeline._answer_explanatory and
backend/services/rag_service._answer_context_only (both make a real LLM call
per question over marts/context that are static within a session -- rule 8:
precompute/reuse rather than recompute on every request).

Reuses Qdrant (already a hard dependency, see embeddings/build_vector_store.py)
instead of adding a new cache dependency (standards.md: an already-installed
tool beats a new one). One extra collection, `rag_answer_cache`, storing the
question's embedding + the full result payload as the point.

Cache partitions live in a `namespace` payload field (filtered on read, not a
separate collection per namespace) -- callers pass `collection` for the NYC/
London explanatory path and `f"context_only:{city_id}"` for the context-only
tier, so a cached JFK answer for NYC never leaks into London's cache or a
different city's.

0.97 cosine threshold: measured against text-embedding-3-small directly
(see demo() below) -- true restatements of the same question (case/
punctuation/filler-word changes, e.g. "why is JFK Airport so busy" vs "why
is JFK airport so busy") score 0.95-0.99, while questions that are merely
about the same entity but ask something different (e.g. "why is JFK so
busy" vs "why is JFK such an important hub in the network" -- busyness vs.
network centrality are different questions) score 0.6-0.7. This is a
near-duplicate cache, not a broad related-question retriever like
build_vector_store.search()'s k-NN -- a false hit here silently serves a
stale answer to a materially different question, so 0.97 sits just below
the true-restatement floor with headroom. 24h TTL: this repo's
underlying marts/insight docs only change on an offline dbt/regeneration run
(rule 8), never mid-session, so nothing goes stale within a day; 24h just
bounds how long a cache entry outlives a regeneration run someone kicked off
without also clearing the cache.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

from config import QDRANT_URL

COLLECTION = "rag_answer_cache"
EMBED_DIM = 1536  # matches embeddings/build_vector_store.py's OpenAI model
SIMILARITY_THRESHOLD = 0.97
TTL_SECONDS = 24 * 60 * 60


_EMBED_RETRY_ATTEMPTS = 4
_EMBED_RETRY_BASE_DELAY_S = 2.0


def _embed(text: str) -> list[float]:
    """Retries with backoff on a 429 -- DeepSeek has no embeddings endpoint
    to fail over to (confirmed against DeepSeek's own API docs 2026-08-14),
    so a rate limit here is worth retrying on OpenAI itself rather than
    dropping the cache lookup or substituting an incompatible-dimension
    vector. See embeddings/build_vector_store.py's _embed for the same
    pattern (kept separate here since this module embeds one string at a
    time, not a batch)."""
    import time

    from openai import OpenAI, RateLimitError

    from config import OPENAI_EMBEDDING_MODEL

    client = OpenAI()
    for attempt in range(1, _EMBED_RETRY_ATTEMPTS + 1):
        try:
            resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=[text])
            return resp.data[0].embedding
        except RateLimitError:
            if attempt == _EMBED_RETRY_ATTEMPTS:
                raise
            time.sleep(_EMBED_RETRY_BASE_DELAY_S * attempt)


def _get_client(url: str = QDRANT_URL):
    from qdrant_client import QdrantClient

    return QdrantClient(url=url)


def _ensure_collection(client, collection: str = COLLECTION) -> None:
    from qdrant_client.models import Distance, VectorParams

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )


def _point_id(namespace: str, question: str) -> int:
    """Deterministic id from namespace+question so re-put()ing the same
    question overwrites its existing cache entry instead of duplicating it.
    Truncated to 63 bits to stay inside Qdrant's unsigned point-id range."""
    digest = hashlib.sha256(f"{namespace}:{question}".encode("utf-8")).hexdigest()
    return int(digest, 16) & ((1 << 63) - 1)


def get(question: str, namespace: str, url: str = QDRANT_URL) -> dict[str, Any] | None:
    """Returns the cached result dict (with cache_hit/cache_similarity added)
    on a near-duplicate, fresh-enough hit within `namespace`; None on a miss
    (no cached entry close enough, or the closest one expired)."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = _get_client(url)
    _ensure_collection(client)

    q_emb = _embed(question)
    hits = client.query_points(
        collection_name=COLLECTION,
        query=q_emb,
        limit=1,
        query_filter=Filter(must=[FieldCondition(key="namespace", match=MatchValue(value=namespace))]),
        score_threshold=SIMILARITY_THRESHOLD,
    ).points
    if not hits:
        return None

    payload = hits[0].payload
    if time.time() - payload["cached_at"] > TTL_SECONDS:
        return None  # expired hit treated as a miss, not silently served

    result = dict(payload["result"])
    result["cache_hit"] = True
    result["cache_similarity"] = float(hits[0].score)
    return result


def put(question: str, namespace: str, result: dict[str, Any], url: str = QDRANT_URL) -> None:
    from qdrant_client.models import PointStruct

    client = _get_client(url)
    _ensure_collection(client)

    q_emb = _embed(question)
    point = PointStruct(
        id=_point_id(namespace, question),
        vector=q_emb,
        payload={"namespace": namespace, "question": question, "cached_at": time.time(), "result": result},
    )
    client.upsert(collection_name=COLLECTION, points=[point])


def demo() -> None:
    ns = "demo_ns"
    fake_result = {"question": "why is JFK Airport so busy", "route": "explanatory", "answer": "fake answer", "sql": None, "rows": None, "sources": []}
    put("why is JFK Airport so busy", ns, fake_result)

    exact = get("why is JFK Airport so busy", ns)
    assert exact is not None, "exact-match question must hit"
    assert exact["cache_hit"] is True
    assert exact["answer"] == "fake answer"
    print(f"exact match: cache_hit={exact['cache_hit']} similarity={exact['cache_similarity']:.4f}")

    # A true restatement (case/wording variant of the same question), not a
    # different-question-about-the-same-entity like "why is JFK such an
    # important hub" (measured cosine 0.647 -- see module docstring) --
    # that pair is below the near-duplicate threshold on purpose.
    paraphrase = get("why is JFK airport so busy", ns)
    assert paraphrase is not None, "near-duplicate restatement must hit"
    assert paraphrase["cache_hit"] is True
    print(f"paraphrase match: cache_hit={paraphrase['cache_hit']} similarity={paraphrase['cache_similarity']:.4f}")

    different = get("what is the weather like in London today", ns)
    assert different is None, "unrelated question must miss"
    print("unrelated question: miss (None), as expected")


if __name__ == "__main__":
    demo()
