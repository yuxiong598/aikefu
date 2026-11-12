from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..model.ticket import Ticket


def list_tickets(session: Session, client_id: str | None, status: str | None) -> list[Ticket]:
    statement = select(Ticket)
    if client_id is not None:
        statement = statement.where(Ticket.client_id == client_id)
    if status is not None:
        statement = statement.where(Ticket.status == status)
    return list(session.scalars(statement.order_by(Ticket.id.desc())))


def get_ticket(session: Session, client_id: str | None, ticket_id: int) -> Ticket | None:
    statement = select(Ticket).where(Ticket.id == ticket_id)
    if client_id is not None:
        statement = statement.where(Ticket.client_id == client_id)
    return session.scalar(statement)


def insert_ticket_if_new(
    session: Session, client_id: str, request_id: str, content_hash: str,
    title: str, description: str,
) -> int | None:
    # 首先获取 SQLite 写锁，避免并发重试同时创建两张工单。
    return session.scalar(
        insert(Ticket)
        .values(
            client_id=client_id, request_id=request_id, content_hash=content_hash,
            title=title, description=description, status="pending", version=1,
            conversation_snapshot=[],
        )
        .on_conflict_do_nothing(index_elements=[Ticket.client_id, Ticket.request_id])
        .returning(Ticket.id)
    )


def find_request(session: Session, client_id: str, request_id: str) -> Ticket:
    return session.scalars(
        select(Ticket).where(Ticket.client_id == client_id, Ticket.request_id == request_id)
    ).one()


def update_status(
    session: Session, client_id: str | None, ticket_id: int, previous_status: str,
    status: str, version: int,
) -> int | None:
    statement = update(Ticket).where(
        Ticket.id == ticket_id, Ticket.status == previous_status, Ticket.version == version,
    )
    if client_id is not None:
        statement = statement.where(Ticket.client_id == client_id)
    return session.scalar(
        statement
        .values(status=status, version=version + 1)
        .returning(Ticket.id)
    )
