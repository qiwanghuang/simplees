from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import SessionLocal
from app.es_client import es_client
from app.models import Product


def build_product_document(product: Product) -> dict:
    """把 MySQL 商品对象转换成 ES 文档。"""

    brand_name = product.brand.name if product.brand else ""
    category_name = product.category.name if product.category else ""

    return {
        "product_id": product.id,
        "product_name": product.name,
        "brand_id": product.brand_id,
        "brand_name": brand_name,
        "category_id": product.category_id,
        "category_name": category_name,
        "search_text": f"{product.name} {brand_name} {category_name}",
        "status": product.status,
        "updated_at": product.updated_at.isoformat(),
    }


def delete_product_from_es(product_id: str) -> None:
    """从 ES 删除指定商品文档。"""

    es_client.delete(
        index=settings.es_product_index,
        id=product_id,
        ignore=[404],
    )


def sync_product_to_es(product: Product) -> None:
    """把单个商品同步到 ES。"""

    if product.status == "deleted":
        delete_product_from_es(product.id)
        return

    es_client.index(
        index=settings.es_product_index,
        id=product.id,
        document=build_product_document(product),
    )


def sync_product_by_id_to_es(db: Session, product_id: str) -> None:
    """根据商品 UUID 查询 MySQL 最新数据，并同步到 ES。"""

    product = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
        )
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        delete_product_from_es(product_id)
        return

    sync_product_to_es(product)


def sync_products_by_brand_id_to_es(db: Session, brand_id: str) -> int:
    """刷新某个品牌下所有商品的 ES 文档。"""

    product_ids = [
        product_id
        for (product_id,) in (
            db.query(Product.id)
            .filter(Product.brand_id == brand_id)
            .all()
        )
    ]

    for product_id in product_ids:
        sync_product_by_id_to_es(
            db=db,
            product_id=product_id,
        )

    return len(product_ids)


def sync_products_by_category_id_to_es(db: Session, category_id: str) -> int:
    """刷新某个类目下所有商品的 ES 文档。"""

    product_ids = [
        product_id
        for (product_id,) in (
            db.query(Product.id)
            .filter(Product.category_id == category_id)
            .all()
        )
    ]

    for product_id in product_ids:
        sync_product_by_id_to_es(
            db=db,
            product_id=product_id,
        )

    return len(product_ids)


def sync_all_products_to_es() -> None:
    """全量重建商品 ES 文档，用于初始化或修复 ES 数据。"""

    db = SessionLocal()

    try:
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
    sync_all_products_to_es()
