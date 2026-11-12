from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from .config import Settings


class Base(DeclarativeBase):
    """业务 ORM 模型的公共基类。"""


def create_sqlite_engine(database_path: Path) -> Engine:
    """根据数据库文件路径创建同步 SQLite 引擎。"""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(database_path)),
        # 使用 Python 3.12+ 的事务模式，让 DDL 和查询也纳入事务。
        connect_args={"autocommit": False},
    )

    @event.listens_for(sqlite_engine, "connect")
    def enable_foreign_keys(connection: Connection, _: ConnectionPoolEntry) -> None:
        # SQLite 仅允许在事务外切换外键检查，每个新连接都要设置一次。
        previous_autocommit = connection.autocommit
        connection.autocommit = True
        try:
            connection.execute("PRAGMA foreign_keys = ON").close()
        finally:
            connection.autocommit = previous_autocommit

    return sqlite_engine


engine = create_sqlite_engine(Settings().sqlite_path)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """为每次请求提供独立会话，由业务层决定何时提交。"""
    # 请求结束时关闭会话，释放连接并回滚未提交的事务。
    with SessionLocal() as session:
        yield session
