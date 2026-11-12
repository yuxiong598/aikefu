from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64))
    indexed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE")
    )
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    chroma_id: Mapped[str] = mapped_column(String(64), unique=True)


class KnowledgeDeletion(Base):
    __tablename__ = "knowledge_deletions"

    # 保留请求编号，避免删除后旧的确认请求把文档重新建回来。
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
