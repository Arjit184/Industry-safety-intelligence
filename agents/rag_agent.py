"""
SafetyIQ — RAG agent (Week 3 — sentence-transformers version)
Queries ChromaDB using semantic embeddings.
Loaded once, reused forever. Never raises exceptions.

Usage:
    from agents.rag_agent import query_rag
    context = query_rag("H2S elevated Zone C, hot work permit active")
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_collection  = None
_initialized = False


def _initialize():
    global _collection, _initialized
    if _initialized:
        return
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        base    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base, "data", "chroma_db")

        if not os.path.exists(db_path):
            return

        client = chromadb.PersistentClient(path=db_path)
        ef     = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = client.get_collection("safetyiq_corpus", embedding_function=ef)

    except Exception:
        # ChromaDB not available or corpus not built yet — silent fallback
        pass
    finally:
        _initialized = True


def query_rag(plant_state: str, n_results: int = 3) -> str:
    """
    Query ChromaDB with current plant conditions.

    Args:
        plant_state : string describing current conditions
                      e.g. "H2S elevated Zone C, hot work permit PTW-047 active, G-07 offline"
        n_results   : how many matching chunks to return

    Returns:
        Human-readable summary for RiskAssessment.rag_context.
        Empty string on any error.
    """
    if not plant_state or not plant_state.strip():
        return ""

    try:
        _initialize()
        if _collection is None:
            return ""

        results   = _collection.query(query_texts=[plant_state], n_results=n_results)
        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        parts = []
        for doc, meta, dist in zip(docs, metas, distances):
            tag        = meta.get("incident_id") or meta.get("reg_id", "?")
            similarity = round((1 - dist) * 100)
            snippet    = doc[:120].strip()
            if snippet:
                parts.append(f"[{tag} {similarity}%] {snippet}")

        return " | ".join(parts)

    except Exception:
        return ""


if __name__ == "__main__":
    queries = [
        "H2S elevated Zone C, hot work permit active, G-07 offline, shift changeover",
        "confined space entry no pre-entry gas check",
        "gas accumulation explosion hot work permit grinding",
        "normal operations all sensors nominal",
    ]
    print("RAG agent test\n" + "=" * 50)
    for q in queries:
        result = query_rag(q)
        print(f"\nQ: {q[:70]}")
        print(f"R: {result[:150] or '(empty)'}")
    print("\nDone")