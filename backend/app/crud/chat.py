from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..model.chat import ChatTurn, Conversation


def list_conversations(session: Session, client_id: str) -> list[Conversation]:
    last_turn = (
        select(func.max(ChatTurn.id))
        .where(ChatTurn.conversation_id == Conversation.id)
        .scalar_subquery()
    )
    statement = (
        select(Conversation)
        .where(Conversation.client_id == client_id)
        .order_by(last_turn.desc())
    )
    return list(session.scalars(statement))


def get_turns(session: Session, conversation_id: str, *, limit: int | None = None) -> list[ChatTurn]:
    statement = select(ChatTurn).where(ChatTurn.conversation_id == conversation_id)
    if limit is not None:
        return list(reversed(session.scalars(statement.order_by(ChatTurn.id.desc()).limit(limit)).all()))
    return list(session.scalars(statement.order_by(ChatTurn.id)))


def get_turn(session: Session, conversation_id: str, request_id: str) -> ChatTurn | None:
    return session.scalar(
        select(ChatTurn).where(
            ChatTurn.conversation_id == conversation_id, ChatTurn.request_id == request_id
        )
    )


def create_conversation_if_new(
    session: Session, conversation_id: str, client_id: str, title: str
) -> None:
    session.execute(
        insert(Conversation)
        .values(id=conversation_id, client_id=client_id, title=title)
        .on_conflict_do_nothing(index_elements=[Conversation.id])
    )


def save_turn_if_new(
    session: Session, conversation_id: str, request_id: str, question: str,
    answer: str, sources: list[dict],
) -> ChatTurn:
    session.execute(
        insert(ChatTurn)
        .values(
            conversation_id=conversation_id, request_id=request_id,
            question=question, answer=answer, sources=sources,
        )
        .on_conflict_do_nothing(index_elements=[ChatTurn.conversation_id, ChatTurn.request_id])
    )
    return session.scalars(
        select(ChatTurn).where(
            ChatTurn.conversation_id == conversation_id, ChatTurn.request_id == request_id
        )
    ).one()
