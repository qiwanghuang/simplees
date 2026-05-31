from app.config import settings
from app.es_client import es_client


def get_product_index_mapping() -> dict:
    """定义商品搜索索引的字段结构。"""

    return {
        "properties": {
            # 商品 UUID，用来从 ES 搜索结果回查 MySQL。
            "product_id": {
                "type": "keyword",
            },

            # 商品名称，既支持全文搜索，也支持精确匹配。
            "product_name": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },

            # 品牌 UUID，只用于过滤或回查，不参与分词搜索。
            "brand_id": {
                "type": "keyword",
            },

            # 品牌名称，支持用户输入品牌名搜索商品。
            "brand_name": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },

            # 类目 UUID，只用于过滤或回查，不参与分词搜索。
            "category_id": {
                "type": "keyword",
            },

            # 类目名称，支持用户输入类目名搜索商品。
            "category_name": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256,
                    }
                },
            },

            # 组合搜索字段。
            # 后面我们会把 商品名 + 品牌名 + 类目名 拼在一起放到这个字段里。
            "search_text": {
                "type": "text",
            },

            # 商品状态：active=上架，inactive=下架，deleted=已删除。
            # 搜索时只查 active。
            "status": {
                "type": "keyword",
            },

            # 更新时间，方便以后排查 ES 数据是不是最新。
            "updated_at": {
                "type": "date",
            },
        }
    }


def create_product_index() -> None:
    """创建商品搜索索引。"""

    index_name = settings.es_product_index

    # 如果索引已经存在，就不要重复创建。
    if es_client.indices.exists(index=index_name):
        print(f"ES 索引已存在：{index_name}")
        return

    es_client.indices.create(
        index=index_name,
        mappings=get_product_index_mapping(),
    )

    print(f"ES 索引创建完成：{index_name}")


if __name__ == "__main__":
    create_product_index()
