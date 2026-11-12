from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("client_id", "request_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    content_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    version: Mapped[int] = mapped_column(default=1)
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="SET NULL"), nullable=True
    )
    conversation_snapshot: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
