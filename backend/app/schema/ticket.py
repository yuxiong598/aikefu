from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .chat import ChatTurnRead

TicketStatus = Literal["pending", "processing", "completed"]


class CreateTicket(BaseModel):
    request_id: UUID
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
    conversation_id: UUID | None = None


class UpdateTicketStatus(BaseModel):
    status: Literal["processing", "completed"]
    version: int = Field(ge=1, description="详情中读取的版本号，用于检查并发更新")


class TicketSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TicketStatus
    version: int
    created_at: datetime
    updated_at: datetime
    conversation_id: UUID | None


class TicketDetail(TicketSummary):
    description: str
    conversation_snapshot: list[ChatTurnRead]
