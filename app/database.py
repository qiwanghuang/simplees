from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def validate_mysql_database_url(database_url: str) -> None:
    """确认当前项目使用 MySQL 连接地址。"""

    if not database_url.startswith("mysql+pymysql://"):
        raise RuntimeError(
            "DATABASE_URL 必须使用 MySQL 连接地址，例如："
            "mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4"
        )


validate_mysql_database_url(settings.database_url)

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_pre_ping=True,
)

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
