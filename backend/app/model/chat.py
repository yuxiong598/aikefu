from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Conversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(60))


class ChatTurn(Base):
    __tablename__ = "chat_turns"
    __table_args__ = (UniqueConstraint("conversation_id", "request_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE")
    )
    request_id: Mapped[str] = mapped_column(String(36))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict]] = mapped_column(JSON)
