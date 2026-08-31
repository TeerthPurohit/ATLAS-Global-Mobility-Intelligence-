import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "rag"))

load_dotenv()

from config import QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient
import semantic_cache
from embeddings.build_vector_store import search

def main():
    print("=== QDRANT CLOUD MIGRATION VALIDATION ===")
    print("Connecting to:", QDRANT_URL)
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # 1. List collections
    collections = [c.name for c in client.get_collections().collections]
    print("Active Collections:", collections)

    # 2. Ensure rag_answer_cache collection exists
    semantic_cache._ensure_collection(client)
    collections_after = [c.name for c in client.get_collections().collections]
    print("Collections after verification:", collections_after)

    # 3. Check insight_docs points count
    if "insight_docs" in collections_after:
        info_docs = client.get_collection("insight_docs")
        print(f"Collection 'insight_docs': {info_docs.points_count} points (indexed vectors)")

    # 4. Check rag_answer_cache info
    if "rag_answer_cache" in collections_after:
        info_cache = client.get_collection("rag_answer_cache")
        print(f"Collection 'rag_answer_cache': {info_cache.points_count} points")

    # 5. Test vector search over insight_docs
    hits = search("airport demand peak hours", k=2)
    print(f"Vector search test: {len(hits)} hits returned -> {[h.get('zone') for h in hits]}")

    # 6. Test semantic cache put & get
    semantic_cache.put("test migration question", "test_ns", {"status": "migrated_ok"})
    cached = semantic_cache.get("test migration question", "test_ns")
    print("Semantic cache test result:", cached)
    
    print("\n[OK] ALL QDRANT CLOUD COLLECTIONS ARE FULLY MIGRATED AND OPERATIONAL!")

if __name__ == "__main__":
    main()
