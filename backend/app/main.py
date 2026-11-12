from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .database import Base, engine
from .router.auth import router as auth_router
from .router.chat import router as chat_router
from .router.documents import router as documents_router
from .router.health import router as health_router
from .router.knowledge import router as knowledge_router
from .router.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 启动时创建已注册的业务表，已有数据会保留。
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="智能客服知识库与售后工单系统", lifespan=lifespan)

# 服务启动时加载配置，后续业务模块可从应用状态取得同一份配置。
app.state.settings = Settings()
app.include_router(health_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
