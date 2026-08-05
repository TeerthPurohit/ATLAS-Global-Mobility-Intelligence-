"""Embed insight docs into Qdrant (FR-2).

Local sentence-transformer (`all-MiniLM-L6-v2`) rather than an embeddings
API call -- this step runs once at precompute time (rule 8), so there's no
reason to spend API budget on it, and no reason to require a network round
trip at query time either. Qdrant runs as a docker-compose service
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
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import QDRANT_URL  # noqa: E402
from insight_generation.generate_insight_docs import OUTPUT_PATH as INSIGHT_DOCS_PATH  # noqa: E402
from insight_generation.generate_insight_docs import load_insight_docs  # noqa: E402

MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384
COLLECTION = "insight_docs"

_PAYLOAD_FIELDS = (
    "zone_id", "zone_name", "borough", "total_trips", "avg_fare", "avg_distance_miles",
    "top_hours", "top_destination", "pagerank_rank", "pagerank_score", "pagerank_total_zones",
    "sources", "phrased_by",
)


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def _get_client(url: str = QDRANT_URL):
    from qdrant_client import QdrantClient

    return QdrantClient(url=url)


def build_vector_store(docs_path: Path = INSIGHT_DOCS_PATH, url: str = QDRANT_URL) -> int:
    from qdrant_client.models import Distance, PointStruct, VectorParams

    docs = load_insight_docs(docs_path)
    if not docs:
        raise ValueError(f"no insight docs found at {docs_path} -- run generate_insight_docs.py first")

    embeddings = _get_model().encode([d["text"] for d in docs], normalize_embeddings=True, show_progress_bar=False)

    client = _get_client(url)
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    points = [
        PointStruct(
            id=int(doc["zone_id"]),
            vector=emb.tolist(),
            payload={"doc_text": doc["text"], **{k: doc.get(k) for k in _PAYLOAD_FIELDS if k in doc}},
        )
        for doc, emb in zip(docs, embeddings)
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(docs)


def search(query: str, k: int = 3, url: str = QDRANT_URL) -> list[dict]:
    """Cosine-similarity nearest neighbors over the precomputed insight docs.

    Each result's payload includes the real stat values the doc was
    templated from, not just the similarity-ranked text -- so a caller can
    trace the retrieval back to the source numbers (rule 2).
    """
    q_emb = _get_model().encode([query], normalize_embeddings=True)[0].tolist()
    client = _get_client(url)
    hits = client.query_points(collection_name=COLLECTION, query=q_emb, limit=k).points
    return [{"score": float(h.score), **h.payload} for h in hits]


def demo() -> None:
    n = build_vector_store()
    assert n > 0, "must embed at least one insight doc"

    results = search("why is JFK Airport so busy", k=3)
    assert len(results) == 3
    assert results[0]["score"] >= results[1]["score"] >= results[2]["score"], "results must be sorted by score"
    assert all("total_trips" in r for r in results), "payload must carry the real stat values, not just text"

    print(f"embedded {n} insight docs into Qdrant collection '{COLLECTION}' at {QDRANT_URL}")
    print("top matches for 'why is JFK Airport so busy':")
    for r in results:
        print(f"  {r['score']:.3f}  {r['zone_name']} ({r['borough']})  total_trips={r['total_trips']}")


if __name__ == "__main__":
    demo()
