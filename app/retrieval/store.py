import chromadb
from chromadb.utils import embedding_functions

_embedder = embedding_functions.DefaultEmbeddingFunction()
_client = chromadb.EphemeralClient()
_collections: dict[str, object] = {}


def _slug(name: str) -> str:
    return name.replace("/", "-").replace(" ", "-")


def get_or_create_collection(name: str):
    slug = _slug(name)
    if slug not in _collections:
        _collections[slug] = _client.create_collection(name=slug, embedding_function=_embedder)
    return _collections[slug]


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


def collection_size(collection) -> int:
    return collection.count()
