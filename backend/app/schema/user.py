from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints


class Credentials(BaseModel):
    username: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_]{3,32}$")]
    password: SecretStr = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: Literal["customer", "staff"]


class LoginResult(BaseModel):
    token: str
    user: UserRead


class ClaimBrowser(BaseModel):
    browser_id: UUID


class ClaimResult(BaseModel):
    conversations: int
    tickets: int
