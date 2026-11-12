from dataclasses import dataclass
from itertools import batched

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..model.knowledge import KnowledgeChunk, KnowledgeDeletion, KnowledgeDocument


@dataclass(frozen=True)
class DocumentIndexState:
    document_id: int
    content_hash: str
    indexed: bool


@dataclass(frozen=True)
class IndexedChunk:
    chroma_id: str
    document_id: int
    filename: str
    position: int
    text: str


_deletion_requested = (
    select(KnowledgeDeletion.request_id)
    .where(KnowledgeDeletion.request_id == KnowledgeDocument.request_id)
    .exists()
)


def document_summaries(session: Session, request_id: str | None = None):
    chunk_count = (
        select(func.count(KnowledgeChunk.id))
        .where(KnowledgeChunk.document_id == KnowledgeDocument.id)
        .scalar_subquery()
    )
    statement = select(
        KnowledgeDocument.id.label("document_id"),
        KnowledgeDocument.request_id,
        KnowledgeDocument.filename,
        KnowledgeDocument.created_at,
        KnowledgeDocument.indexed,
        _deletion_requested.label("deleting"),
        chunk_count.label("chunk_count"),
    )
    if request_id is not None:
        statement = statement.where(KnowledgeDocument.request_id == request_id)
    return session.execute(statement.order_by(KnowledgeDocument.id.desc())).mappings().all()


def document_chunks(session: Session, document_id: int) -> list[KnowledgeChunk]:
    return list(session.scalars(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == document_id)
        .order_by(KnowledgeChunk.position)
    ))


def get_document(session: Session, request_id: str) -> KnowledgeDocument | None:
    return session.scalar(select(KnowledgeDocument).where(KnowledgeDocument.request_id == request_id))


def deletion_requested(session: Session, request_id: str) -> bool:
    return session.get(KnowledgeDeletion, request_id) is not None


def mark_document_deleting(session: Session, request_id: str) -> None:
    session.execute(
        insert(KnowledgeDeletion)
        .values(request_id=request_id)
        .on_conflict_do_nothing(index_elements=[KnowledgeDeletion.request_id])
    )


def get_indexed_chunks(session: Session, chroma_ids: list[str]) -> dict[str, IndexedChunk]:
    chunks: dict[str, IndexedChunk] = {}
    # 分批绑定 ID，避免候选较多时超过 SQLite 的参数限制。
    for batch in batched(chroma_ids, 500):
        statement = (
            select(
                KnowledgeChunk.chroma_id,
                KnowledgeDocument.id,
                KnowledgeDocument.filename,
                KnowledgeChunk.position,
                KnowledgeChunk.text,
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeChunk.chroma_id.in_(batch),
                KnowledgeDocument.indexed.is_(True),
                ~_deletion_requested,
            )
        )
        for row in session.execute(statement):
            chunks[row.chroma_id] = IndexedChunk(*row)
    return chunks


def save_document_if_new(
    session: Session,
    request_id: str,
    filename: str,
    content_hash: str,
    chunks: list[tuple[str, str]],
) -> DocumentIndexState:
    # 先写入唯一请求编号，避免并发请求同时认为文档尚未创建。
    statement = (
        insert(KnowledgeDocument)
        .values(request_id=request_id, filename=filename, content_hash=content_hash, indexed=False)
        .on_conflict_do_nothing(index_elements=[KnowledgeDocument.request_id])
        .returning(KnowledgeDocument.id)
    )
    document_id = session.scalar(statement)
    if document_id is None:
        row = session.execute(
            select(KnowledgeDocument.id, KnowledgeDocument.content_hash, KnowledgeDocument.indexed)
            .where(KnowledgeDocument.request_id == request_id)
        ).one()
        return DocumentIndexState(row.id, row.content_hash, row.indexed)

    session.add_all(
        KnowledgeChunk(
            document_id=document_id,
            position=position,
            text=text,
            chroma_id=chroma_id,
        )
        for position, (chroma_id, text) in enumerate(chunks, start=1)
    )
    return DocumentIndexState(document_id, content_hash, indexed=False)


def mark_document_indexed(session: Session, document_id: int) -> None:
    session.execute(
        update(KnowledgeDocument)
        .where(KnowledgeDocument.id == document_id)
        .values(indexed=True)
    )
