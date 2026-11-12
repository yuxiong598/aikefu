from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .schema.user import UserRead
from .service.auth import user_for_token

bearer = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def current_user(
    credentials: BearerCredentials, session: Annotated[Session, Depends(get_db)]
) -> UserRead:
    user = user_for_token(session, credentials.credentials) if credentials is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="请登录或重新登录。", headers={"WWW-Authenticate": "Bearer"})
    return user


def staff_user(user: Annotated[UserRead, Depends(current_user)]) -> UserRead:
    if user.role != "staff":
        raise HTTPException(status_code=403, detail="此操作需要客服账号。")
    return user


CurrentUser = Annotated[UserRead, Depends(current_user)]
StaffUser = Annotated[UserRead, Depends(staff_user)]
