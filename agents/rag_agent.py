"""
SafetyIQ — RAG agent
Queries the ChromaDB vector store using TF-IDF embeddings (works fully offline).

Public interface (Member 2 calls this from main.py):
    from agents.rag_agent import query_rag
    context = query_rag(plant_state_string)

The collection and vectorizer are loaded once and reused — never recreated per tick.
Always returns a string, never raises exceptions.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# ── Singletons — loaded once on first call ───────────────────────────────────
_collection  = None
_vectorizer  = None
_initialized = False


def _initialize():
    global _collection, _vectorizer, _initialized
    if _initialized:
        return

    try:
        import chromadb, pickle

        base    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path  = os.path.join(base, "data", "chroma_db")
        vec_path = os.path.join(base, "data", "tfidf_vectorizer.pkl")

        if not os.path.exists(db_path) or not os.path.exists(vec_path):
            _initialized = True
            return

        client       = chromadb.PersistentClient(path=db_path)
        _collection  = client.get_collection("safetyiq_corpus")

        with open(vec_path, "rb") as f:
            _vectorizer = pickle.load(f)

    except Exception:
        pass
    finally:
        _initialized = True


def _embed(text: str):
    """Convert text to normalized TF-IDF vector."""
    vec  = _vectorizer.transform([text]).toarray().astype(float)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


# ── Public function ───────────────────────────────────────────────────────────

def query_rag(plant_state: str, n_results: int = 3) -> str:
    """
    Query ChromaDB with current plant conditions.

    Args:
        plant_state : plain string describing current conditions
                      e.g. "H2S elevated Zone C, hot work permit active, G-07 offline"
        n_results   : number of matching chunks to return

    Returns:
        Human-readable summary for RiskAssessment.rag_context.
        Empty string on any error or if ChromaDB unavailable.
    """
    if not plant_state or not plant_state.strip():
        return ""

    try:
        _initialize()
        if _collection is None or _vectorizer is None:
            return ""

        q_vec   = _embed(plant_state)
        results = _collection.query(query_embeddings=q_vec, n_results=n_results)

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


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    queries = [
        "H2S elevated Zone C, hot work permit active, G-07 offline, shift changeover",
        "confined space entry no pre-entry gas check",
        "gas accumulation explosion hot work permit grinding Zone C",
        "normal operations all sensors nominal shift stable",
    ]
    print("RAG agent test\n" + "=" * 50)
    passed = 0
    for q in queries:
        result = query_rag(q)
        print(f"\nQ: {q[:65]}...")
        print(f"R: {result[:150]}")
        if result:
            passed += 1

    print(f"\n{passed}/{len(queries)} queries returned results")
    print("RAG agent: PASS" if passed >= 3 else "RAG agent: FAIL")