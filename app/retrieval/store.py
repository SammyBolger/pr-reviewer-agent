import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

_embedder = embedding_functions.DefaultEmbeddingFunction()
_client = chromadb.PersistentClient(path=str(settings.chroma_path))
_collections: dict[str, object] = {}


def _slug(name: str) -> str:
    return name.replace("/", "-").replace(" ", "-")


def get_or_create_collection(name: str):
    slug = _slug(name)
    if slug not in _collections:
        _collections[slug] = _client.get_or_create_collection(name=slug, embedding_function=_embedder)
    return _collections[slug]


def reset_collection(name: str) -> None:
    slug = _slug(name)
    if slug in _collections:
        del _collections[slug]
    try:
        _client.delete_collection(name=slug)
    except Exception:
        pass


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
