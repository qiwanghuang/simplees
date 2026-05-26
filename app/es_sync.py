from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import SessionLocal
from app.es_client import es_client
from app.models import Product


def build_product_document(product: Product) -> dict:
    """把数据库里的商品对象转换成 ES 文档。"""

    brand_name = product.brand.name if product.brand else ""
    category_name = product.category.name if product.category else ""

    return {
        # 商品 UUID。ES 搜索后会返回这个 ID，再用它回查 SQLite。
        "product_id": product.id,

        # 商品名称。
        "product_name": product.name,

        # 品牌 UUID 和品牌名称。
        "brand_id": product.brand_id,
        "brand_name": brand_name,

        # 类目 UUID 和类目名称。
        "category_id": product.category_id,
        "category_name": category_name,

        # 组合搜索字段。
        # 用户输入商品名、品牌名、类目名时，都可以通过这个字段命中商品。
        "search_text": f"{product.name} {brand_name} {category_name}",

        # 商品状态。搜索时只搜索 active。
        "status": product.status,

        # 更新时间。ES 的 date 字段可以接收 ISO 格式字符串。
        "updated_at": product.updated_at.isoformat(),
    }


def sync_product_to_es(product: Product) -> None:
    """同步单个商品到 ES。"""

    index_name = settings.es_product_index

    # 如果商品已经删除，就从 ES 删除对应文档。
    if product.status == "deleted":
        es_client.delete(
            index=index_name,
            id=product.id,
            ignore=[404],
        )
        return

    # 普通新增或更新，都使用 index。
    # id 使用商品 UUID，这样重复同步同一个商品时会覆盖旧文档。
    es_client.index(
        index=index_name,
        id=product.id,
        document=build_product_document(product),
    )


def sync_product_by_id_to_es(db: Session, product_id: str) -> None:
    """根据商品 UUID 重新查询数据库，并把最新商品数据同步到 ES。"""

    product = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
        )
        .filter(Product.id == product_id)
        .first()
    )

    # 如果数据库里已经没有这个商品，就删除 ES 里的同 ID 文档。
    if product is None:
        es_client.delete(
            index=settings.es_product_index,
            id=product_id,
            ignore=[404],
        )
        return

    # 如果商品还在数据库里，就按最新数据库数据覆盖 ES 文档。
    sync_product_to_es(product)


def sync_all_products_to_es() -> None:
    """把数据库里所有商品同步到 ES。"""

    db = SessionLocal()

    try:
        # joinedload 的作用是一次性把商品关联的品牌和类目也查出来。
        # 否则循环商品时可能会产生很多额外查询。
        products = (
            db.query(Product)
            .options(
                joinedload(Product.brand),
                joinedload(Product.category),
            )
            .all()
        )

        for product in products:
            sync_product_to_es(product)

        print(f"商品同步完成，共同步 {len(products)} 条商品到 ES")

    finally:
        db.close()


if __name__ == "__main__":
    # 允许执行：python3 -m app.es_sync
    sync_all_products_to_es()
