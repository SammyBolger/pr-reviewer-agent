import chromadb
from chromadb.utils import embedding_functions

_embedder = embedding_functions.DefaultEmbeddingFunction()


def new_collection(name: str = "repo-context"):
    client = chromadb.EphemeralClient()
    return client.create_collection(name=name, embedding_function=_embedder)


def add(collection, chunks: list[dict]) -> None:
    if not chunks:
        return
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["meta"] for c in chunks],
    )


def query(collection, text: str, k: int = 5) -> list[dict]:
    r = collection.query(query_texts=[text], n_results=k)
    hits = []
    for i, doc in enumerate(r["documents"][0]):
        hits.append({
            "text": doc,
            "meta": r["metadatas"][0][i],
        })
    return hits
