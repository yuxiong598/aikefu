from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..crud.ticket import list_tickets
from ..database import get_db
from ..dependencies import CurrentUser, StaffUser
from ..schema.ticket import CreateTicket, TicketDetail, TicketStatus, TicketSummary, UpdateTicketStatus
from ..service.ticket import (
    TicketConflict, TicketNotFound, change_status, create_ticket, read_ticket,
)

router = APIRouter(prefix="/tickets", tags=["售后工单"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[TicketSummary], summary="查看售后工单")
def tickets(
    user: CurrentUser, session: DatabaseSession,
    status: Annotated[TicketStatus | None, Query()] = None,
):
    return list_tickets(session, None if user.role == "staff" else user.id, status)


@router.get("/{ticket_id}", summary="查看工单及会话快照")
def detail(ticket_id: int, user: CurrentUser, session: DatabaseSession) -> TicketDetail:
    try:
        return read_ticket(session, None if user.role == "staff" else user.id, ticket_id)
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail="工单不存在。") from exc


@router.post("", summary="创建售后工单")
def create(payload: CreateTicket, user: CurrentUser, session: DatabaseSession) -> TicketDetail:
    try:
        return create_ticket(session, user.id, payload)
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail="关联会话不存在。") from exc
    except TicketConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{ticket_id}/status", summary="更新工单处理状态")
def update(
    ticket_id: int, payload: UpdateTicketStatus,
    user: StaffUser, session: DatabaseSession,
) -> TicketDetail:
    try:
        return change_status(session, None, ticket_id, payload)
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail="工单不存在。") from exc
    except TicketConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
