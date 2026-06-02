from elasticsearch import Elasticsearch

from app.config import settings


def create_es_client() -> Elasticsearch:
    """创建 Elasticsearch 客户端。"""

    # 如果 .env 里配置了 ES_USERNAME 和 ES_PASSWORD，就使用账号密码连接。
    # 如果没有配置，就按本地无账号密码的 ES 来连接。
    if settings.es_username and settings.es_password:
        return Elasticsearch(
            settings.es_host,
            basic_auth=(settings.es_username, settings.es_password),
            request_timeout=settings.es_request_timeout_seconds,
        )

    return Elasticsearch(
        settings.es_host,
        request_timeout=settings.es_request_timeout_seconds,
    )


# 全局 ES 客户端。
# 后面创建索引、写入商品索引、搜索商品都会用它。
es_client = create_es_client()


def ping_es() -> bool:
    """检查 Elasticsearch 是否可以连接。"""
    return es_client.ping()
