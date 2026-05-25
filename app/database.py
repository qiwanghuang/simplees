from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def ensure_sqlite_parent_dir(database_url: str) -> None:
    """如果使用 SQLite，自动创建数据库文件所在目录。"""
    # 只有 SQLite 文件数据库才需要提前创建父目录。
    # MySQL/PostgreSQL/Oracle 这类远程数据库不需要这个处理。
    if not database_url.startswith("sqlite:///"):
        return

    db_path = database_url.replace("sqlite:///", "", 1)

    # SQLite 的内存数据库不对应真实文件，也不需要创建目录。
    if db_path == ":memory:":
        return

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


# 在创建数据库连接之前，先确保 SQLite 文件目录存在。
ensure_sqlite_parent_dir(settings.database_url)

# engine 是 SQLAlchemy 的数据库引擎。
# 它负责管理底层数据库连接，后续所有数据库操作都会基于它执行。
engine = create_engine(
    settings.database_url,
    # SQLite 默认限制同一个连接只能在创建它的线程中使用。
    # FastAPI 本地开发时可能跨线程处理请求，所以这里关闭这个限制。
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)

# SessionLocal 是数据库会话工厂。
# 每次请求进来时创建一个 Session，用完后关闭。
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型类的父类。"""

    pass


def get_db():
    """FastAPI 依赖函数：为每个请求提供一个数据库 Session。"""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
