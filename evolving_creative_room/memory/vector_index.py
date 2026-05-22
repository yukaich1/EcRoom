from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path
from typing import Iterable

import numpy as np


class VectorIndex:
    """Persistent Chroma index with deterministic local embeddings.

    The storage boundary is intentionally isolated so it can be swapped for
    Tencent Cloud VectorDB without changing MemoryStore/KnowledgeBase.
    """

    def __init__(self, root: Path | str, collection_name: str, dimensions: int = 384) -> None:
        self.root = Path(root)
        self.collection_name = collection_name
        self.dimensions = dimensions
        self.available = False
        self.collection = None
        self.error = ""
        self.backend = os.environ.get("ECROOM_VECTOR_BACKEND", "chroma").strip().lower() or "chroma"
        self._memory_rows: dict[str, dict[str, object]] = {}
        if self.backend == "memory":
            self.available = True
            return
        if self.backend == "tencent":
            try:
                from evolving_creative_room.memory.tencent_vector import TencentVectorIndex

                self.collection = TencentVectorIndex(self.root, collection_name, dimensions)
                self.available = True
            except Exception as exc:
                self.collection = None
                self.error = str(exc)
            return
        try:
            import chromadb

            self.root.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.root))
            self.collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
            self.available = True
        except Exception as exc:
            self.collection = None
            self.error = str(exc)

    def upsert(self, *, record_id: str, document: str, metadata: dict[str, object] | None = None) -> None:
        if not self.available or not document.strip():
            return
        if self.backend == "memory":
            self._memory_rows[record_id] = {
                "document": document,
                "metadata": _clean_metadata(metadata or {}),
                "embedding": embed_text(document, self.dimensions),
            }
            return
        if not self.collection:
            return
        if self.backend == "tencent":
            self.collection.upsert(
                record_id=record_id,
                document=document,
                embedding=embed_text(document, self.dimensions),
                metadata=_clean_metadata(metadata or {}),
            )
            return
        self.collection.upsert(
            ids=[record_id],
            documents=[document],
            embeddings=[embed_text(document, self.dimensions)],
            metadatas=[_clean_metadata(metadata or {})],
        )

    def upsert_many(self, rows: Iterable[tuple[str, str, dict[str, object]]]) -> None:
        if not self.available:
            return
        if self.backend == "memory":
            for record_id, document, metadata in rows:
                self.upsert(record_id=record_id, document=document, metadata=metadata)
            return
        if not self.collection:
            return
        ids, documents, embeddings, metadatas = [], [], [], []
        for record_id, document, metadata in rows:
            if not record_id or not document.strip():
                continue
            ids.append(record_id)
            documents.append(document)
            embeddings.append(embed_text(document, self.dimensions))
            metadatas.append(_clean_metadata(metadata))
        if ids:
            self.collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query(self, text: str, *, limit: int = 12, where: dict[str, object] | None = None) -> list[dict[str, object]]:
        if not self.available or not text.strip():
            return []
        if self.backend == "memory":
            return self._query_memory(text, limit=limit, where=where)
        if not self.collection:
            return []
        if self.backend == "tencent":
            return self.collection.query(embedding=embed_text(text, self.dimensions), limit=max(limit, 1), where=_clean_metadata(where or {}) or None)
        result = self.collection.query(
            query_embeddings=[embed_text(text, self.dimensions)],
            n_results=max(limit, 1),
            where=_clean_metadata(where or {}) or None,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[dict[str, object]] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for index, record_id in enumerate(ids):
            hits.append(
                {
                    "record_id": record_id,
                    "document": documents[index] if index < len(documents) else "",
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                    "distance": distances[index] if index < len(distances) else 1.0,
                    "vector_score": 1.0 - float(distances[index] if index < len(distances) else 1.0),
                }
            )
        return hits

    def _query_memory(
        self,
        text: str,
        *,
        limit: int = 12,
        where: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        query_vector = np.array(embed_text(text, self.dimensions), dtype=np.float32)
        where_clean = _clean_metadata(where or {})
        scored: list[dict[str, object]] = []
        for record_id, row in self._memory_rows.items():
            metadata = dict(row.get("metadata", {}) or {})
            if where_clean and any(metadata.get(key) != value for key, value in where_clean.items()):
                continue
            embedding = np.array(row.get("embedding", []), dtype=np.float32)
            vector_score = float(np.dot(query_vector, embedding)) if embedding.size == query_vector.size else 0.0
            scored.append(
                {
                    "record_id": record_id,
                    "document": str(row.get("document", "")),
                    "metadata": metadata,
                    "distance": 1.0 - vector_score,
                    "vector_score": vector_score,
                }
            )
        scored.sort(key=lambda item: float(item["vector_score"]), reverse=True)
        return scored[: max(limit, 1)]


def embed_text(text: str, dimensions: int = 384) -> list[float]:
    vector = np.zeros(dimensions, dtype=np.float32)
    tokens = _tokens(text)
    if not tokens:
        return vector.tolist()
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        index = value % dimensions
        sign = 1.0 if (value >> 8) & 1 else -1.0
        vector[index] += sign
    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector /= norm
    return vector.tolist()


def _tokens(text: str) -> list[str]:
    normalized = text.lower()
    words = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", normalized)
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    bigrams = [cjk[index : index + 2] for index in range(max(0, len(cjk) - 1))]
    return words + bigrams


def _clean_metadata(metadata: dict[str, object]) -> dict[str, str | int | float | bool]:
    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        elif value is None:
            continue
        else:
            cleaned[key] = ";".join(str(item) for item in value) if isinstance(value, list) else str(value)
    return cleaned
