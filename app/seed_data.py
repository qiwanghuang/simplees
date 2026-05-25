from decimal import Decimal
from random import choice, randint

from app.database import SessionLocal
from app.models import Brand, Category, Product


BRAND_NAMES = [
    "Apple",
    "华为",
    "小米",
    "OPPO",
    "vivo",
    "荣耀",
    "联想",
    "戴尔",
    "索尼",
    "三星",
]

CATEGORY_NAMES = [
    "手机",
    "电脑",
    "平板",
    "耳机",
    "手表",
    "相机",
    "键盘",
    "鼠标",
    "显示器",
    "音箱",
]

PRODUCT_WORDS = [
    "Pro",
    "Max",
    "Ultra",
    "青春版",
    "旗舰版",
    "标准版",
    "无线版",
    "智能版",
    "轻薄版",
    "高性能版",
]


def seed_data() -> None:
    """初始化品牌、类目和 100 条商品测试数据。"""
    db = SessionLocal()

    try:
        # 如果已经有商品数据，就不重复初始化。
        product_count = db.query(Product).count()
        if product_count > 0:
            print(f"数据库中已经有 {product_count} 条商品数据，跳过初始化")
            return

        # 创建品牌数据。
        brands = [
            Brand(
                name=brand_name,
                description=f"{brand_name} 品牌",
                status="active",
            )
            for brand_name in BRAND_NAMES
        ]

        # 创建类目数据。
        categories = [
            Category(
                name=category_name,
                status="active",
            )
            for category_name in CATEGORY_NAMES
        ]

        db.add_all(brands)
        db.add_all(categories)

        # flush 的作用是把 brands/categories 先写入数据库会话。
        # 这样后面创建商品时，可以拿到它们自动生成的 UUID。
        db.flush()

        products = []

        # 创建 100 条商品数据。
        for index in range(1, 101):
            brand = choice(brands)
            category = choice(categories)
            product_word = choice(PRODUCT_WORDS)

            product = Product(
                name=f"{brand.name}{category.name}{product_word} {index}",
                description=f"这是一款来自 {brand.name} 的{category.name}商品，适合测试 ES 搜索。",
                price=Decimal(randint(99, 9999)),
                brand_id=brand.id,
                category_id=category.id,
                status="active",
            )

            products.append(product)

        db.add_all(products)
        db.commit()

        print("测试数据初始化完成：10 个品牌，10 个类目，100 条商品")

    except Exception:
        # 如果中途出错，回滚本次写入，避免数据库只写入一半。
        db.rollback()
        raise

    finally:
        # 不管成功失败，都要关闭数据库连接。
        db.close()


if __name__ == "__main__":
    seed_data()