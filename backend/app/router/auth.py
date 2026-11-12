from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import BearerCredentials, CurrentUser
from ..schema.user import ClaimBrowser, ClaimResult, Credentials, LoginResult, UserRead
from ..service.auth import (
    AccountConflict, InvalidCredentials, claim_browser, create_account, login, logout,
)

router = APIRouter(prefix="/auth", tags=["用户登录"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/register", summary="注册普通用户")
def register(payload: Credentials, session: DatabaseSession) -> UserRead:
    try:
        return create_account(session, payload)
    except AccountConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/login", summary="登录")
def sign_in(payload: Credentials, session: DatabaseSession, request: Request) -> LoginResult:
    try:
        return login(session, payload, request.app.state.settings.auth_session_hours)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="用户名或密码不正确。") from exc


@router.get("/me", summary="查看当前账号")
def me(user: CurrentUser) -> UserRead:
    return user


@router.post("/logout", status_code=204, summary="退出登录")
def sign_out(user: CurrentUser, credentials: BearerCredentials, session: DatabaseSession) -> None:
    logout(session, credentials.credentials)


@router.post("/claim-browser", summary="认领本浏览器的历史聊天和工单")
def claim(payload: ClaimBrowser, user: CurrentUser, session: DatabaseSession) -> ClaimResult:
    try:
        return claim_browser(session, user.id, str(payload.browser_id))
    except AccountConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
