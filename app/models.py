import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """生成字符串形式的 UUID，作为所有表的主键。"""
    return str(uuid.uuid4())


class Brand(Base):
    """品牌表。"""

    __tablename__ = "brands"

    # 品牌 UUID，主键，不使用自增 ID。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # 品牌名称，例如：Apple、小米、华为。
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 品牌描述，可以为空。
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 品牌状态：active=启用，inactive=停用，deleted=已删除。
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # 创建时间。
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # 更新时间。后面更新数据时，我们手动刷新这个字段。
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # 一个品牌下面可以有多个商品。
    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Category(Base):
    """类目表。"""

    __tablename__ = "categories"

    # 类目 UUID，主键，不使用自增 ID。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # 类目名称，例如：手机、电脑、耳机。
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 父级类目 UUID。
    # 第一版可以先不使用，保留这个字段方便以后做多级类目。
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # 类目状态：active=启用，inactive=停用，deleted=已删除。
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # 创建时间。
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # 更新时间。后面更新数据时，我们手动刷新这个字段。
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # 一个类目下面可以有多个商品。
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """商品表。"""

    __tablename__ = "products"

    # 商品 UUID，主键，不使用自增 ID。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # 商品名称，例如：iPhone 15 Pro。
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # 商品描述，可以为空。
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 商品价格。
    # Numeric 更适合表示金额，比 float 更稳。
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # 商品所属品牌 UUID。
    brand_id: Mapped[str] = mapped_column(String(36), ForeignKey("brands.id"), nullable=False)

    # 商品所属类目 UUID。
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id"), nullable=False)

    # 商品状态：active=上架，inactive=下架，deleted=已删除。
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # 创建时间。
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # 更新时间。后面更新数据时，我们手动刷新这个字段。
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # 商品关联的品牌对象。
    brand: Mapped[Brand] = relationship(back_populates="products")

    # 商品关联的类目对象。
    category: Mapped[Category] = relationship(back_populates="products")