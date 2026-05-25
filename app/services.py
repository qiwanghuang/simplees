from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.es_client import es_client
from app.models import Product


def normalize_page(page: int) -> int:
    """修正页码，保证页码最小是 1。"""

    if page < 1:
        return 1

    return page


def normalize_size(size: int) -> int:
    """修正每页数量，避免一次返回太多数据。"""

    if size < 1:
        return settings.search_default_page_size

    if size > settings.search_max_page_size:
        return settings.search_max_page_size

    return size


def normalize_keyword(keyword: str) -> str:
    """清理搜索关键词，去掉前后空格。"""

    return keyword.strip()


def compact_keyword(keyword: str) -> str:
    """去掉关键词中的空白字符，用于商品名精确包含匹配。"""

    return "".join(keyword.split())


def search_product_ids_from_es(keyword: str, page: int, size: int) -> tuple[list[str], int]:
    """从 ES 搜索商品 UUID。"""

    keyword = normalize_keyword(keyword)
    exact_keyword = compact_keyword(keyword)
    page = normalize_page(page)
    size = normalize_size(size)

    # ES 的分页参数：
    # from 表示从第几条开始，size 表示返回多少条。
    from_index = (page - 1) * size

    response = es_client.search(
        index=settings.es_product_index,
        query={
            "bool": {
                "should": [
                    {
                        # 强匹配：商品名称中直接包含用户输入的完整关键词时，优先返回。
                        # 例如“小米手机”只会匹配商品名里连续出现“小米手机”的商品。
                        "wildcard": {
                            "product_name.keyword": {
                                "value": f"*{exact_keyword}*",
                                "boost": 10,
                            }
                        }
                    },
                    {
                        "multi_match": {
                            # 用户输入的搜索关键词。
                            "query": keyword,

                            # AND 表示分词后的内容都要命中。
                            # 这样“小米手机”不会只因为命中“小米”或“手机”就返回。
                            "operator": "and",

                            # 商品名权重最高，组合字段兜底。
                            "fields": [
                                "product_name^3",
                                "search_text",
                            ],
                        }
                    }
                ],
                # 至少满足一个 should 条件。
                # 也就是要么商品名完整包含关键词，要么分词后全部命中。
                "minimum_should_match": 1,
                "filter": [
                    {
                        # 只搜索上架商品。
                        "term": {
                            "status": "active",
                        }
                    }
                ],
            }
        },
        from_=from_index,
        size=size,
    )

    hits = response["hits"]["hits"]

    product_ids = [
        hit["_source"]["product_id"]
        for hit in hits
    ]

    total = response["hits"]["total"]["value"]

    return product_ids, total


def get_products_by_ids(db: Session, product_ids: list[str]) -> list[Product]:
    """根据商品 UUID 列表查询 SQLite，并保持 ES 返回的排序。"""

    if not product_ids:
        return []

    products = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
        )
        .filter(Product.id.in_(product_ids))
        .filter(Product.status == "active")
        .all()
    )

    # SQLite 查询结果不一定会按 product_ids 的顺序返回。
    # 这里手动按 ES 的相关性顺序重新排序。
    product_map = {
        product.id: product
        for product in products
    }

    return [
        product_map[product_id]
        for product_id in product_ids
        if product_id in product_map
    ]


def search_products(db: Session, keyword: str, page: int, size: int) -> tuple[list[Product], int]:
    """搜索商品：先查 ES 获取商品 UUID，再回查 SQLite 获取商品详情。"""

    product_ids, total = search_product_ids_from_es(
        keyword=keyword,
        page=page,
        size=size,
    )

    products = get_products_by_ids(
        db=db,
        product_ids=product_ids,
    )

    return products, total


def list_products(db: Session, page: int, size: int) -> tuple[list[Product], int]:
    """分页查询商品列表：直接查询 SQLite，不走 ES。"""

    page = normalize_page(page)
    size = normalize_size(size)

    # SQL 分页参数：
    # offset 表示跳过多少条，limit 表示本次最多返回多少条。
    offset = (page - 1) * size

    base_query = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
        )
        .filter(Product.status != "deleted")
    )

    total = base_query.count()

    products = (
        base_query
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    return products, total


def get_product_by_id(db: Session, product_id: str) -> Product | None:
    """根据商品 UUID 查询商品详情。"""

    return (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
        )
        .filter(Product.id == product_id)
        .filter(Product.status != "deleted")
        .first()
    )
