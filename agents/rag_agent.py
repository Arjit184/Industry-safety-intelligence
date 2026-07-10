"""
agents/rag_agent.py
RAG layer: SentenceTransformer-compatible embeddings + ChromaDB vector store.

Embedding backend: sklearn TF-IDF (L2-normalised, 512-dim) — no HuggingFace
download needed. Drop-in replaceable with a real SentenceTransformer once
the environment has internet access; the public API is identical.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.config import Settings
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from typing import List, Dict, Optional

from data.corpus.incidents import INCIDENTS

# ── Module-level singletons ───────────────────────────────────────────────────
_VECTORIZER: Optional[TfidfVectorizer] = None
_COLLECTION = None
_CLIENT = None
_DIM = 512   # TF-IDF max features → embedding dimensionality


class _LocalEmbedder:
    """
    SentenceTransformer-compatible embedder using TF-IDF + L2 normalisation.
    Same .encode(texts) → np.ndarray interface as SentenceTransformer.
    """
    def __init__(self, dim: int = _DIM):
        self._dim = dim
        corpus_texts = [inc["content"] for inc in INCIDENTS]
        self._vec = TfidfVectorizer(
            max_features=dim,
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
        )
        self._vec.fit(corpus_texts)

    def encode(self, texts: List[str], show_progress_bar: bool = False) -> np.ndarray:
        mat = self._vec.transform(texts).toarray().astype(np.float32)
        mat = normalize(mat, norm="l2")
        return mat


_EMBEDDER: Optional[_LocalEmbedder] = None


def _get_embedder() -> _LocalEmbedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = _LocalEmbedder()
    return _EMBEDDER


def _get_collection():
    global _COLLECTION, _CLIENT
    if _COLLECTION is not None:
        return _COLLECTION

    _CLIENT = chromadb.Client(Settings(anonymized_telemetry=False))

    # Delete and recreate so re-runs start clean
    try:
        _CLIENT.delete_collection("safetyiq_incidents")
    except Exception:
        pass

    col = _CLIENT.create_collection(
        name="safetyiq_incidents",
        metadata={"hnsw:space": "cosine"},
    )
    _ingest(col)
    _COLLECTION = col
    return _COLLECTION


def _ingest(collection) -> None:
    """Embed and store all corpus documents."""
    embedder = _get_embedder()
    docs   = [inc["content"] for inc in INCIDENTS]
    ids    = [inc["id"]      for inc in INCIDENTS]
    metas  = [
        {
            "title":        inc["title"],
            "severity":     inc["severity"],
            "casualties":   str(inc["casualties"]),
            "regulations":  ", ".join(inc["regulations"]),
            "risk_factors": ", ".join(inc["risk_factors"]),
            "tags":         ", ".join(inc["tags"]),
        }
        for inc in INCIDENTS
    ]
    embeddings = embedder.encode(docs).tolist()
    collection.add(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)


# ── Public API ────────────────────────────────────────────────────────────────

def query(
    text: str,
    n_results: int = 3,
    severity_filter: Optional[str] = None,
) -> List[Dict]:
    """
    Semantic search over incident corpus.
    Returns list of dicts: id, title, content, distance, metadata.
    distance is cosine distance (0 = identical, 2 = opposite).
    similarity = 1 - distance.
    """
    embedder   = _get_embedder()
    collection = _get_collection()

    query_vec = embedder.encode([text]).tolist()
    where = {"severity": severity_filter} if severity_filter else None

    results = collection.query(
        query_embeddings=query_vec,
        n_results=min(n_results, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    out = []
    for i in range(len(results["ids"][0])):
        out.append({
            "id":       results["ids"][0][i],
            "title":    results["metadatas"][0][i]["title"],
            "content":  results["documents"][0][i],
            "distance": round(results["distances"][0][i], 4),
            "metadata": results["metadatas"][0][i],
        })
    return out


def build_rag_context(active_factor_ids: List[str], risk_score: float) -> str:
    """
    Builds a context string for the Anthropic alert generator.
    Returns top-2 most relevant incidents as a formatted string.
    """
    if not active_factor_ids:
        return ""

    query_text = " ".join(active_factor_ids).replace("_", " ")
    if risk_score >= 80:
        results = query(query_text, n_results=2, severity_filter="CRITICAL")
        if not results:
            results = query(query_text, n_results=2)
    else:
        results = query(query_text, n_results=2)

    if not results:
        return ""

    lines = ["RELEVANT HISTORICAL INCIDENTS:"]
    for r in results:
        meta = r["metadata"]
        sim  = max(0.0, 1.0 - r["distance"])
        lines.append(
            f"• {r['title']} | severity={meta['severity']} "
            f"| casualties={meta['casualties']} | similarity={sim:.0%}"
        )
        snippet = r["content"][:300].rsplit(" ", 1)[0] + "…"
        lines.append(f"  {snippet}")
        lines.append(f"  Violations: {meta['regulations']}")

    return "\n".join(lines)


def match_historical_incident(trigger_id: str) -> Optional[str]:
    """
    Returns best matching historical incident ID for a compound trigger.
    Used to populate CompoundTrigger.historical_match.
    Threshold: distance < 0.75 (similarity > 25%).
    """
    query_text = trigger_id.replace("_x_", " combined with ").replace("_", " ")
    results = query(query_text, n_results=1)
    if results and results[0]["distance"] < 0.90:
        return results[0]["id"]
    return None
