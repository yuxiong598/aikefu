from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from .knowledge import KnowledgeHit


class ChatQuestion(BaseModel):
    request_id: UUID
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ChatSource(KnowledgeHit):
    citation: int


class ChatTurnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    sources: list[ChatSource]


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str


class ConversationDetail(ConversationSummary):
    turns: list[ChatTurnRead]
