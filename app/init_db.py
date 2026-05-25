from app.database import Base, engine

# 必须导入 models。
# 只有导入了 models.py，SQLAlchemy 才知道有哪些表需要创建。
from app import models  # noqa: F401


def init_db() -> None:
    """根据 ORM 模型创建数据库表。"""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    # 允许我们直接执行：python -m app.init_db
    init_db()
    print("数据库表创建完成")