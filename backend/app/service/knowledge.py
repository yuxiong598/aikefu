import hashlib
import json
import logging
from threading import Lock

from sqlalchemy.orm import Session

from ..crud.knowledge import (
    deletion_requested,
    document_chunks,
    document_summaries,
    get_document,
    get_indexed_chunks,
    mark_document_deleting,
    mark_document_indexed,
    save_document_if_new,
)
from ..rag.embedding import encode_documents, encode_query
from ..rag.vector_store import ChromaStore
from ..schema.document import ChunkPreview, DocumentDetail, DocumentSummary
from ..schema.knowledge import KnowledgeHit

INDEX_BATCH_SIZE = 64
logger = logging.getLogger(__name__)
_store: ChromaStore | None = None
_store_lock = Lock()
_mutation_lock = Lock()


class ConfirmationConflict(Exception):
    """同一个请求编号已用于不同的文档内容。"""


class KnowledgeIndexError(Exception):
    """正文已保存，向量索引暂未完成。"""


class DocumentNotFound(Exception):
    """没有找到文档。"""


class DocumentDeleting(Exception):
    """该请求对应的文档正在删除或已删除。"""


class KnowledgeDeletionError(Exception):
    """向量清理未完成，可继续删除。"""


def _get_store() -> ChromaStore:
    global _store
    # 同一进程复用本地 Chroma 客户端，避免并发初始化。
    with _store_lock:
        if _store is None:
            _store = ChromaStore()
        return _store


def confirm_document(
    session: Session, request_id: str, filename: str, chunks: list[str]
) -> int:
    payload = json.dumps([filename, chunks], ensure_ascii=True, separators=(",", ":"))
    content_hash = hashlib.sha256(payload.encode("ascii")).hexdigest()
    # 重试使用相同的 Chroma ID，覆盖可能已写入的批次。
    entries = [(f"{request_id}:{position}", text) for position, text in enumerate(chunks, start=1)]

    with _mutation_lock:
        # 先保存正文，失败后可按原请求或从管理页重试。
        with session.begin():
            if deletion_requested(session, request_id):
                raise DocumentDeleting
            document = save_document_if_new(session, request_id, filename, content_hash, entries)
            if document.content_hash != content_hash:
                raise ConfirmationConflict

        if not document.indexed:
            _index_document(session, document.document_id, entries)
        return document.document_id


def _index_document(session: Session, document_id: int, entries: list[tuple[str, str]]) -> None:
    try:
        store = _get_store()
        for offset in range(0, len(entries), INDEX_BATCH_SIZE):
            batch = entries[offset : offset + INDEX_BATCH_SIZE]
            ids = [chroma_id for chroma_id, _ in batch]
            texts = [text for _, text in batch]
            store.upsert(ids, encode_documents(texts))
    except Exception as exc:
        logger.exception("文档 %s 的向量索引失败", document_id)
        raise KnowledgeIndexError from exc

    with session.begin():
        mark_document_indexed(session, document_id)


def _summary(row) -> DocumentSummary:
    status = "pending"
    if row["deleting"]:
        status = "deleting"
    elif row["indexed"]:
        status = "indexed"
    return DocumentSummary(**row, status=status)


def list_documents(session: Session) -> list[DocumentSummary]:
    return [_summary(row) for row in document_summaries(session)]


def read_document(session: Session, request_id: str) -> DocumentDetail:
    rows = document_summaries(session, request_id)
    if not rows:
        raise DocumentNotFound
    summary = _summary(rows[0])
    chunks = [
        ChunkPreview(index=chunk.position, text=chunk.text)
        for chunk in document_chunks(session, summary.document_id)
    ]
    return DocumentDetail(**summary.model_dump(), chunks=chunks)


def retry_document(session: Session, request_id: str) -> DocumentDetail:
    with _mutation_lock:
        with session.begin():
            document = get_document(session, request_id)
            if document is None:
                raise DocumentNotFound
            if deletion_requested(session, request_id):
                raise DocumentDeleting
            document_id = document.id
            already_indexed = document.indexed
            entries = [
                (chunk.chroma_id, chunk.text) for chunk in document_chunks(session, document_id)
            ] if not already_indexed else []

        if not already_indexed:
            _index_document(session, document_id, entries)
        return read_document(session, request_id)


def delete_document(session: Session, request_id: str) -> None:
    with _mutation_lock:
        with session.begin():
            document = get_document(session, request_id)
            if document is None:
                if deletion_requested(session, request_id):
                    return
                raise DocumentNotFound
            ids = [chunk.chroma_id for chunk in document_chunks(session, document.id)]
            # 先持久化删除意图，清理中断时检索会跳过该文档。
            mark_document_deleting(session, request_id)

        try:
            if ids:
                store = _get_store()
                for offset in range(0, len(ids), INDEX_BATCH_SIZE):
                    store.delete(ids[offset : offset + INDEX_BATCH_SIZE])
        except Exception as exc:
            logger.exception("文档 %s 的向量清理失败", request_id)
            raise KnowledgeDeletionError from exc

        with session.begin():
            document = get_document(session, request_id)
            if document is not None:
                # 外键级联清理 SQLite 中的片段。
                session.delete(document)


def search_knowledge(session: Session, query: str, top_k: int) -> list[KnowledgeHit]:
    embedding = encode_query(query)
    store = _get_store()
    candidate_count = top_k
    while True:
        candidates = store.search(embedding, top_k=candidate_count)
        with session.begin():
            indexed = get_indexed_chunks(session, [match.chroma_id for match in candidates])

        hits = []
        # 保留 Chroma 的排序，只返回 SQLite 中已完成索引的正文。
        for match in candidates:
            chunk = indexed.get(match.chroma_id)
            if chunk is not None:
                hits.append(
                    KnowledgeHit(
                        document_id=chunk.document_id,
                        filename=chunk.filename,
                        position=chunk.position,
                        text=chunk.text,
                        distance=match.distance,
                    )
                )
                if len(hits) == top_k:
                    return hits

        if len(candidates) < candidate_count:
            return hits
        # 被过滤的片段可能排在前面，扩大候选范围以补齐结果。
        candidate_count *= 2
