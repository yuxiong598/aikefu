import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..model.chat import Conversation
from ..model.ticket import Ticket
from ..model.user import BrowserClaim, LoginSession, User
from ..schema.user import ClaimResult, Credentials, LoginResult, UserRead


class AccountConflict(Exception):
    """账号或历史数据归属冲突。"""


class InvalidCredentials(Exception):
    """登录凭据不正确。"""


def _password_hash(password: str, salt: str) -> str:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32
    ).hex()


def create_account(session: Session, credentials: Credentials, role: str = "customer") -> UserRead:
    salt = secrets.token_hex(16)
    user = User(
        id=str(uuid4()), username=credentials.username.lower(),
        password_salt=salt, password_hash=_password_hash(credentials.password.get_secret_value(), salt),
        role=role,
    )
    try:
        with session.begin():
            session.add(user)
            session.flush()
            return UserRead.model_validate(user)
    except IntegrityError as exc:
        raise AccountConflict("用户名已存在。") from exc


def login(session: Session, credentials: Credentials, hours: int) -> LoginResult:
    with session.begin():
        user = session.scalar(select(User).where(User.username == credentials.username.lower()))
        # 不存在的账号也执行一次密码计算，统一登录失败的处理。
        salt = user.password_salt if user is not None else "0" * 32
        candidate = _password_hash(credentials.password.get_secret_value(), salt)
        if user is None or not hmac.compare_digest(candidate, user.password_hash):
            raise InvalidCredentials
        token = secrets.token_urlsafe(32)
        session.add(LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours),
        ))
        return LoginResult(token=token, user=UserRead.model_validate(user))


def user_for_token(session: Session, token: str) -> UserRead | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # 依赖校验结束后关闭事务，业务服务可独立开启写事务。
    with session.begin():
        user = session.scalar(
            select(User).join(LoginSession, LoginSession.user_id == User.id)
            .where(
                LoginSession.token_hash == token_hash,
                LoginSession.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        return UserRead.model_validate(user) if user is not None else None


def logout(session: Session, token: str) -> None:
    with session.begin():
        session.execute(delete(LoginSession).where(
            LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
        ))


def claim_browser(session: Session, user_id: str, browser_id: str) -> ClaimResult:
    try:
        with session.begin():
            inserted = session.scalar(
                insert(BrowserClaim).values(browser_id=browser_id, user_id=user_id)
                .on_conflict_do_nothing(index_elements=[BrowserClaim.browser_id])
                .returning(BrowserClaim.browser_id)
            )
            claim = session.get(BrowserClaim, browser_id)
            if claim.user_id != user_id or session.get(User, browser_id) is not None:
                raise AccountConflict("该历史数据编号已关联账号。")
            if inserted is None:
                return ClaimResult(conversations=0, tickets=0)
            chats = session.execute(
                update(Conversation).where(Conversation.client_id == browser_id).values(client_id=user_id)
            ).rowcount
            tickets = session.execute(
                update(Ticket).where(Ticket.client_id == browser_id).values(client_id=user_id)
            ).rowcount
            return ClaimResult(conversations=chats, tickets=tickets)
    except IntegrityError as exc:
        raise AccountConflict("历史工单请求编号冲突，认领未完成。") from exc
