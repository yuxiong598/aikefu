import hashlib

from sqlalchemy.orm import Session

from ..crud.chat import get_turns
from ..crud.ticket import find_request, get_ticket, insert_ticket_if_new, update_status
from ..model.chat import Conversation
from ..schema.chat import ChatTurnRead
from ..schema.ticket import CreateTicket, TicketDetail, UpdateTicketStatus


class TicketNotFound(Exception):
    """工单或关联会话不属于当前浏览器。"""


class TicketConflict(Exception):
    """请求编号冲突或状态已被更新。"""


def read_ticket(session: Session, client_id: str | None, ticket_id: int) -> TicketDetail:
    ticket = get_ticket(session, client_id, ticket_id)
    if ticket is None:
        raise TicketNotFound
    return TicketDetail.model_validate(ticket)


def create_ticket(session: Session, client_id: str, payload: CreateTicket) -> TicketDetail:
    content_hash = hashlib.sha256(
        payload.model_dump_json(exclude={"request_id"}).encode("utf-8")
    ).hexdigest()
    with session.begin():
        ticket_id = insert_ticket_if_new(
            session, client_id, str(payload.request_id), content_hash,
            payload.title, payload.description,
        )
        ticket = find_request(session, client_id, str(payload.request_id))
        if ticket.content_hash != content_hash:
            raise TicketConflict("该请求编号已用于不同的工单内容。")

        if ticket_id is not None and payload.conversation_id is not None:
            conversation = session.get(Conversation, str(payload.conversation_id))
            if conversation is None or conversation.client_id != client_id:
                raise TicketNotFound
            ticket.conversation_id = conversation.id
            # 保存建单时最近 20 轮会话快照，后续聊天不会改变这份上下文。
            ticket.conversation_snapshot = [
                ChatTurnRead.model_validate(turn).model_dump(mode="json")
                for turn in get_turns(session, conversation.id, limit=20)
            ]
        session.flush()
        return TicketDetail.model_validate(ticket)


def change_status(
    session: Session, client_id: str | None, ticket_id: int, payload: UpdateTicketStatus
) -> TicketDetail:
    previous = "pending" if payload.status == "processing" else "processing"
    with session.begin():
        changed = update_status(
            session, client_id, ticket_id, previous, payload.status, payload.version
        )
        ticket = get_ticket(session, client_id, ticket_id)
        if ticket is None:
            raise TicketNotFound
        # 相同更新的网络重试返回已完成的结果。
        if changed is None and not (
            ticket.status == payload.status and ticket.version == payload.version + 1
        ):
            raise TicketConflict("工单状态已变化，请刷新详情后重试。")
        return TicketDetail.model_validate(ticket)
