import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromadb
from chromadb.config import Settings
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from typing import List, Dict, Optional
from data.corpus.incidents import INCIDENTS

_EMBEDDER = None
_COLLECTION = None
_CLIENT = None

class _LocalEmbedder:
    """TF-IDF embedder with identical .encode() interface to SentenceTransformer."""
    def __init__(self, dim=512):
        corpus_texts = [inc["content"] for inc in INCIDENTS]
        self._vec = TfidfVectorizer(max_features=dim, ngram_range=(1,2), sublinear_tf=True, strip_accents="unicode")
        self._vec.fit(corpus_texts)

    def encode(self, texts: List[str], show_progress_bar=False) -> np.ndarray:
        mat = self._vec.transform(texts).toarray().astype(np.float32)
        return normalize(mat, norm="l2")

def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = _LocalEmbedder()
    return _EMBEDDER

def _get_collection():
    global _COLLECTION, _CLIENT
    if _COLLECTION is not None:
        return _COLLECTION
    _CLIENT = chromadb.Client(Settings(anonymized_telemetry=False))
    try: _CLIENT.delete_collection("safetyiq_incidents")
    except: pass
    col = _CLIENT.create_collection(name="safetyiq_incidents", metadata={"hnsw:space":"cosine"})
    embedder = _get_embedder()
    docs  = [inc["content"] for inc in INCIDENTS]
    ids   = [inc["id"]      for inc in INCIDENTS]
    metas = [{"title":inc["title"],"severity":inc["severity"],"casualties":str(inc["casualties"]),
               "regulations":", ".join(inc["regulations"]),"risk_factors":", ".join(inc["risk_factors"]),
               "tags":", ".join(inc["tags"])} for inc in INCIDENTS]
    col.add(documents=docs, embeddings=embedder.encode(docs).tolist(), ids=ids, metadatas=metas)
    _COLLECTION = col
    return _COLLECTION

def query(text: str, n_results: int = 3, severity_filter: Optional[str] = None) -> List[Dict]:
    embedder, collection = _get_embedder(), _get_collection()
    where = {"severity": severity_filter} if severity_filter else None
    results = collection.query(query_embeddings=embedder.encode([text]).tolist(),
        n_results=min(n_results, collection.count()), where=where,
        include=["documents","metadatas","distances"])
    out = []
    for i in range(len(results["ids"][0])):
        out.append({"id":results["ids"][0][i],"title":results["metadatas"][0][i]["title"],
                    "content":results["documents"][0][i],"distance":round(results["distances"][0][i],4),
                    "metadata":results["metadatas"][0][i]})
    return out

def build_rag_context(active_factor_ids: List[str], risk_score: float) -> str:
    if not active_factor_ids:
        return ""
    query_text = " ".join(active_factor_ids).replace("_"," ")
    results = query(query_text, n_results=2, severity_filter="CRITICAL") if risk_score >= 80 else query(query_text, n_results=2)
    if not results:
        results = query(query_text, n_results=2)
    if not results:
        return ""
    lines = ["RELEVANT HISTORICAL INCIDENTS:"]
    for r in results:
        meta = r["metadata"]
        sim  = max(0.0, 1.0 - r["distance"])
        lines.append(f"• {r['title']} | severity={meta['severity']} | casualties={meta['casualties']} | similarity={sim:.0%}")
        lines.append(f"  {r['content'][:300].rsplit(' ',1)[0]}…")
        lines.append(f"  Violations: {meta['regulations']}")
    return "\n".join(lines)

def match_historical_incident(trigger_id: str) -> Optional[str]:
    query_text = trigger_id.replace("_x_"," combined with ").replace("_"," ")
    results = query(query_text, n_results=1)
    if results and results[0]["distance"] < 0.90:
        return results[0]["id"]
    return None
