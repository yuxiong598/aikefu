from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..crud.chat import list_conversations
from ..database import get_db
from ..dependencies import CurrentUser
from ..schema.chat import ChatQuestion, ChatTurnRead, ConversationDetail, ConversationSummary
from ..service.chat import ConversationNotFound, QuestionConflict, ask, read_conversation
from ..service.deepseek import DeepSeekResponseError, DeepSeekUnavailable

router = APIRouter(prefix="/chat/conversations", tags=["客服问答"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ConversationSummary], summary="查看会话列表")
def conversations(user: CurrentUser, session: DatabaseSession):
    return list_conversations(session, user.id)


@router.get("/{conversation_id}", summary="查看会话消息")
def conversation(conversation_id: UUID, user: CurrentUser, session: DatabaseSession) -> ConversationDetail:
    try:
        return read_conversation(session, str(conversation_id), user.id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="会话不存在。") from exc


@router.post("/{conversation_id}/messages", summary="提问并保存带引用的回答")
def message(
    conversation_id: UUID, payload: ChatQuestion, request: Request,
    user: CurrentUser, session: DatabaseSession,
) -> ChatTurnRead:
    try:
        return ask(
            session, request.app.state.settings, str(conversation_id), user.id,
            str(payload.request_id), payload.question,
        )
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="会话不存在。") from exc
    except QuestionConflict as exc:
        raise HTTPException(status_code=409, detail="该请求编号已用于其他问题。") from exc
    except DeepSeekUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DeepSeekResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
