from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import Settings

COLLECTION_NAME = "knowledge_chunks"


@dataclass(frozen=True)
class VectorMatch:
    chroma_id: str
    distance: float


class ChromaStore:
    """保存知识片段 ID 和向量，使用余弦距离检索。"""

    def __init__(self, path: Path | None = None) -> None:
        storage_path = path if path is not None else Settings().chroma_dir
        client = chromadb.PersistentClient(
            path=str(storage_path.resolve()),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # 向量由 BGE 生成，正文留给 SQLite，Chroma 只按片段 ID 建索引。
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            configuration={"hnsw": {"space": "cosine"}},
            embedding_function=None,
        )

    def upsert(self, ids: list[str], embeddings: list[list[float]]) -> None:
        """写入向量，同一个 ID 再次写入时更新对应向量。"""
        if len(ids) != len(embeddings):
            raise ValueError("片段 ID 与向量的数量必须相同。")
        if ids:
            self._collection.upsert(ids=ids, embeddings=embeddings)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorMatch]:
        """返回最相近的片段 ID 和余弦距离，距离越小越相近。"""
        if top_k < 1:
            raise ValueError("top_k 必须大于零。")
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["distances"],
        )
        distances = result["distances"]
        if distances is None:
            raise RuntimeError("Chroma 未返回检索距离。")
        return [
            VectorMatch(chroma_id, distance)
            for chroma_id, distance in zip(result["ids"][0], distances[0], strict=True)
        ]

    def delete(self, ids: list[str]) -> None:
        """按片段 ID 删除对应向量。"""
        if ids:
            self._collection.delete(ids=ids)
