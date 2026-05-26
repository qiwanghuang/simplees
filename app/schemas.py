from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BrandInfo(BaseModel):
    """接口返回用的品牌信息。"""

    id: str
    name: str

    # 允许 Pydantic 从 SQLAlchemy ORM 对象读取字段。
    model_config = ConfigDict(from_attributes=True)


class CategoryInfo(BaseModel):
    """接口返回用的类目信息。"""

    id: str
    name: str

    # 允许 Pydantic 从 SQLAlchemy ORM 对象读取字段。
    model_config = ConfigDict(from_attributes=True)


class ProductListItem(BaseModel):
    """商品搜索列表里的单个商品。"""

    id: str
    name: str
    description: str | None
    price: Decimal | None
    status: str
    brand: BrandInfo
    category: CategoryInfo

    # 允许 Pydantic 从 SQLAlchemy ORM 对象读取字段。
    model_config = ConfigDict(from_attributes=True)


class ProductDetail(BaseModel):
    """商品详情接口返回的商品信息。"""

    id: str
    name: str
    description: str | None
    price: Decimal | None
    status: str
    brand: BrandInfo
    category: CategoryInfo
    created_at: datetime
    updated_at: datetime

    # 允许 Pydantic 从 SQLAlchemy ORM 对象读取字段。
    model_config = ConfigDict(from_attributes=True)


class ProductSearchResponse(BaseModel):
    """商品搜索接口返回结构。"""

    items: list[ProductListItem]
    total: int
    page: int
    size: int


class ProductUpdateRequest(BaseModel):
    """商品更新接口的请求结构。"""

    # 商品名称。
    name: str

    # 商品描述，可以为空。
    description: str | None = None

    # 商品价格，可以为空。
    price: Decimal | None = None

    # 商品所属品牌 UUID。
    brand_id: str

    # 商品所属类目 UUID。
    category_id: str

    # 商品状态：active=上架，inactive=下架，deleted=已删除。
    status: str


class MessageResponse(BaseModel):
    """通用消息返回结构。"""

    message: str
