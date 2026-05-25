from app.config import settings
from app.es_client import es_client


def test_search(keyword: str) -> None:
    """测试 ES 是否可以根据关键词搜索商品。"""

    response = es_client.search(
        index=settings.es_product_index,
        query={
            "bool": {
                # must 表示必须满足的搜索条件。
                "must": [
                    {
                        "multi_match": {
                            # 用户输入的关键词。
                            "query": keyword,

                            # 搜索这些字段。
                            # ^3 表示商品名称权重更高。
                            "fields": [
                                "product_name^3",
                                "brand_name^2",
                                "category_name^2",
                                "search_text",
                            ],
                        }
                    }
                ],

                # filter 表示过滤条件，不参与相关性评分。
                # 这里只搜索 active 状态的商品。
                "filter": [
                    {
                        "term": {
                            "status": "active",
                        }
                    }
                ],
            }
        },
        size=5,
    )

    hits = response["hits"]["hits"]

    print(f"关键词：{keyword}")
    print(f"命中数量：{response['hits']['total']['value']}")
    print("前 5 条结果：")

    for hit in hits:
        source = hit["_source"]

        print(
            "-",
            source["product_id"],
            source["product_name"],
            source["brand_name"],
            source["category_name"],
            "score=",
            hit["_score"],
        )


if __name__ == "__main__":
    # 你可以把这里的关键词改成：手机、Apple、华为、电脑、小米 等。
    test_search("手机")