"""
SafetyIQ — corpus embedder
Member 2 owns this file.

Embeds all RAG chunks into a ChromaDB vector store.
Run once. Re-run with --reset to rebuild.

Run:
    python3 data/embed_corpus.py           # embed everything
    python3 data/embed_corpus.py --reset   # wipe and rebuild
    python3 data/embed_corpus.py --query "hot work gas confined space"

Output: data/chroma_db/  (auto-created, add to .gitignore)
"""

import json, argparse, sys, os, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sanitize_metadata(raw: dict) -> dict:
    """
    ChromaDB metadata values must be str, int, float, or bool.
    Convert everything else: lists/dicts/sets/tuples → JSON string,
    None → empty string, datetime → isoformat string.
    Primitives (str, int, float, bool) are passed through unchanged.
    """
    import datetime
    clean = {}
    for k, v in raw.items():
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif v is None:
            clean[k] = ""
        elif isinstance(v, datetime.datetime):
            clean[k] = v.isoformat()
        elif isinstance(v, datetime.date):
            clean[k] = v.isoformat()
        elif isinstance(v, (list, dict, set, tuple)):
            clean[k] = json.dumps(v, default=str)
        else:
            clean[k] = str(v)
    return clean


def get_embedding_function():
    from chromadb.utils import embedding_functions
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_collection(db_path: str = "data/chroma_db"):
    import chromadb
    client = chromadb.PersistentClient(path=db_path)
    ef     = get_embedding_function()
    try:
        col = client.get_collection("safetyiq_corpus", embedding_function=ef)
    except Exception:
        col = client.create_collection("safetyiq_corpus", embedding_function=ef)
    return col


def embed(chunks_path: str = "data/corpus/chunks.json",
          db_path:     str = "data/chroma_db",
          reset:       bool = False) -> None:

    try:
        import chromadb
    except ImportError:
        print("ERROR: pip install chromadb sentence-transformers")
        sys.exit(1)

    if not Path(chunks_path).exists():
        print(f"ERROR: {chunks_path} not found — run corpus_builder.py first")
        sys.exit(1)

    with open(chunks_path) as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks")

    if reset and Path(db_path).exists():
        import shutil; shutil.rmtree(db_path)
        print("DB wiped")

    client = chromadb.PersistentClient(path=db_path)
    ef     = get_embedding_function()

    try:
        col = client.get_collection("safetyiq_corpus", embedding_function=ef)
        if reset:
            client.delete_collection("safetyiq_corpus")
            col = client.create_collection("safetyiq_corpus", embedding_function=ef)
    except Exception:
        col = client.create_collection("safetyiq_corpus", embedding_function=ef)

    existing = set(col.get()["ids"]) if col.count() > 0 else set()
    new      = [c for c in chunks if c["id"] not in existing]

    if not new:
        print(f"All {len(chunks)} chunks already embedded. Use --reset to rebuild.")
        return

    BATCH = 32
    print(f"Embedding {len(new)} new chunks...")
    t0 = time.time()
    for i in range(0, len(new), BATCH):
        batch = new[i:i+BATCH]

        batch_ids       = [c["id"]   for c in batch]
        batch_documents = [c["text"] for c in batch]
        batch_metadatas = [sanitize_metadata(c.get("metadata", {})) for c in batch]

        print(f"  batch {i//BATCH + 1}: {len(batch)} chunks, metadata keys: {list(batch_metadatas[0].keys())}")

        col.add(
            ids       = batch_ids,
            documents = batch_documents,
            metadatas = batch_metadatas,
        )
        print(f"  {min(i+BATCH, len(new))}/{len(new)} embedded")

    print(f"Done in {time.time()-t0:.1f}s — {col.count()} total chunks in DB")

    # Smoke test
    print("\nSmoke test: 'hot work permit gas accumulation'")
    res = col.query(query_texts=["hot work permit gas accumulation"], n_results=3)
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        tag = meta.get("incident_id") or meta.get("reg_id", "?")
        print(f"  [{tag}] {doc[:90]}...")
    print("\nEmbed: PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset",  action="store_true")
    parser.add_argument("--query",  type=str, default=None)
    parser.add_argument("--chunks", default="data/corpus/chunks.json")
    parser.add_argument("--db",     default="data/chroma_db")
    args = parser.parse_args()

    if args.query:
        col = get_collection(args.db)
        res = col.query(query_texts=[args.query], n_results=5)
        print(f"\nTop 5 for: '{args.query}'\n")
        for i, (doc, meta, dist) in enumerate(zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )):
            tag = meta.get("incident_id") or meta.get("reg_id", "?")
            print(f"{i+1}. [{tag}] score={1-dist:.3f}\n   {doc[:110]}...\n")
    else:
        embed(args.chunks, args.db, args.reset)