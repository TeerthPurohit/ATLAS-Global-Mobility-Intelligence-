"""Embed insight docs into Qdrant (FR-2).

Uses OpenAI's `text-embedding-3-small` (1536-dim) -- this step runs once at
precompute time (rule 8), so the API cost is a one-off batch call, not a
per-request charge. Qdrant runs as a docker-compose service
(`qdrant/qdrant`, port 6333, persistent volume) and is reached via
`QDRANT_URL` (`rag/config.py`, defaults to `http://localhost:6333` for
local dev outside Docker).

Every point's payload carries the same real stat values the doc's text was
templated from (total_trips, avg_fare, busiest hours, PageRank rank, top
destination) alongside the doc text -- so a retrieval hit is traceable back
to real numbers, not just similarity-ranked prose (rule 2).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OPENAI_EMBEDDING_MODEL, QDRANT_API_KEY, QDRANT_URL
from insight_generation.generate_insight_docs import OUTPUT_PATH as INSIGHT_DOCS_PATH
from insight_generation.generate_insight_docs import load_insight_docs

MODEL_NAME = OPENAI_EMBEDDING_MODEL
EMBED_DIM = 1536
COLLECTION = "insight_docs"
# How far past k to oversample from Qdrant before reranking narrows back
# down -- wide enough for TF-IDF to find a lexically-exact hit the embedding
# ranked lower, capped so the per-query TF-IDF fit stays cheap.
_RERANK_OVERSAMPLE = 4
_RERANK_MAX_CANDIDATES = 20
# Weight on the embedding's own cosine score vs. TF-IDF lexical overlap --
# embeddings capture meaning, TF-IDF anchors exact-name matches (a query
# naming a specific zone/station should never lose to a generically similar
# paragraph about a different one). Product tuning, not a measured constant,
# same honesty bar as pricing_engine's capped adjustment rates.
_RERANK_SEMANTIC_WEIGHT = 0.7


_EMBED_RETRY_ATTEMPTS = 4
_EMBED_RETRY_BASE_DELAY_S = 2.0


def _embed(texts: list[str]) -> list[list[float]]:
    """OpenAI embeddings are already unit-normalized, so cosine distance in
    Qdrant works directly on the raw vectors.

    Retries with backoff on a 429 -- DeepSeek (this repo's usual chat-
    completion fallback, see llm_client.py) has no embeddings endpoint at
    all (confirmed against DeepSeek's own API docs 2026-08-14: only Chat
    Completions/Responses/FIM/Models/Balance), so there is no provider to
    fail over to; a rate limit here is transient and worth retrying on
    OpenAI itself rather than giving up or, worse, silently substituting a
    different-dimension embedding into a 1536-dim Qdrant collection."""
    import time

    from openai import OpenAI, RateLimitError

    client = OpenAI()
    for attempt in range(1, _EMBED_RETRY_ATTEMPTS + 1):
        try:
            resp = client.embeddings.create(model=MODEL_NAME, input=texts)
            return [d.embedding for d in resp.data]
        except RateLimitError:
            if attempt == _EMBED_RETRY_ATTEMPTS:
                raise
            time.sleep(_EMBED_RETRY_BASE_DELAY_S * attempt)


def _get_client(url: str = QDRANT_URL):
    from qdrant_client import QdrantClient

    return QdrantClient(url=url, api_key=QDRANT_API_KEY)


def _point_id(doc: dict) -> int:
    """NYC docs key on zone_id (int). station_id is accepted as a fallback
    so a future station-based city needs no change here."""
    raw = doc.get("zone_id", doc.get("station_id"))
    if raw is None:
        raise ValueError(f"doc has neither zone_id nor station_id: {doc.keys()}")
    return int(raw)


def build_vector_store(docs_path: Path = INSIGHT_DOCS_PATH, url: str = QDRANT_URL, collection: str = COLLECTION) -> int:
    from qdrant_client.models import Distance, PointStruct, VectorParams

    docs = load_insight_docs(docs_path)
    if not docs:
        raise ValueError(f"no insight docs found at {docs_path} -- run generate_insight_docs.py first")

    embeddings = _embed([d["text"] for d in docs])

    client = _get_client(url)
    client.recreate_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    points = [
        PointStruct(
            id=_point_id(doc),
            vector=emb,
            payload={"doc_text": doc["text"], **{k: v for k, v in doc.items() if k != "text"}},
        )
        for doc, emb in zip(docs, embeddings)
    ]
    client.upsert(collection_name=collection, points=points)
    return len(docs)


def _rerank(query: str, candidates: list[dict], k: int) -> list[dict]:
    """Hybrid rerank: blend each candidate's real embedding cosine score
    (already in candidate["score"], left untouched) with a real TF-IDF
    lexical-overlap score against the query, fit fresh on just this
    candidate set (a request-time rerank, not a trained/persisted model --
    rule 8). Adds 'rerank_score' rather than overwriting 'score', so both
    real numbers stay visible."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [c["doc_text"] for c in candidates]
    try:
        matrix = TfidfVectorizer(stop_words="english").fit_transform([query] + texts)
        lexical_scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    except ValueError:
        # Degenerate case: query/docs share no vocabulary after stopword
        # removal (e.g. a purely numeric query) -- fall back to the
        # original semantic ranking rather than failing the request.
        return candidates[:k]

    blended = [
        {**c, "rerank_score": round(_RERANK_SEMANTIC_WEIGHT * c["score"] + (1 - _RERANK_SEMANTIC_WEIGHT) * float(lex), 4)}
        for c, lex in zip(candidates, lexical_scores)
    ]
    blended.sort(key=lambda c: c["rerank_score"], reverse=True)
    return blended[:k]


def search(
    query: str, k: int = 3, url: str = QDRANT_URL, collection: str = COLLECTION, rerank: bool = True,
) -> list[dict]:
    """Nearest neighbors over the precomputed insight docs in the given
    city's collection (default: NYC's). Oversamples from Qdrant's cosine
    ranking, then reranks with a real lexical signal (see _rerank) before
    narrowing back to k -- set rerank=False to get raw cosine order.

    Each result's payload includes the real stat values the doc was
    templated from, not just the similarity-ranked text -- so a caller can
    trace the retrieval back to the source numbers (rule 2).
    """
    q_emb = _embed([query])[0]
    client = _get_client(url)
    fetch_k = min(k * _RERANK_OVERSAMPLE, _RERANK_MAX_CANDIDATES) if rerank else k
    hits = client.query_points(collection_name=collection, query=q_emb, limit=fetch_k).points
    candidates = [{"score": float(h.score), **h.payload} for h in hits]
    if rerank and len(candidates) > k:
        return _rerank(query, candidates, k)
    return candidates[:k]


def demo() -> None:
    n = build_vector_store()
    assert n > 0, "must embed at least one insight doc"

    results = search("why is JFK Airport so busy", k=3)
    assert len(results) == 3
    assert results[0]["rerank_score"] >= results[1]["rerank_score"] >= results[2]["rerank_score"], (
        "results must be sorted by the blended rerank score"
    )
    assert all("total_trips" in r for r in results), "payload must carry the real stat values, not just text"

    raw = search("why is JFK Airport so busy", k=3, rerank=False)
    assert raw[0]["score"] >= raw[1]["score"] >= raw[2]["score"], "raw (rerank=False) must stay in cosine order"
    assert "rerank_score" not in raw[0], "rerank=False must not add a rerank_score"

    print(f"embedded {n} insight docs into Qdrant collection '{COLLECTION}' at {QDRANT_URL}")
    print("top matches for 'why is JFK Airport so busy' (reranked):")
    for r in results:
        print(f"  cosine={r['score']:.3f} rerank={r['rerank_score']:.3f}  {r['zone_name']} ({r['borough']})  total_trips={r['total_trips']}")


if __name__ == "__main__":
    demo()
