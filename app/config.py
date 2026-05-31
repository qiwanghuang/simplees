import os
from dataclasses import dataclass

from dotenv import load_dotenv


# 读取项目根目录下的 .env 文件。
# 这样配置可以写在 .env 里，代码里只负责读取，不把配置值写死。
load_dotenv()


def get_int_env(name: str, default: int) -> int:
    """读取整数类型的环境变量。"""
    value = os.getenv(name)

    # 如果 .env 里没有配置这个值，就使用代码里给定的默认值。
    if value is None or value == "":
        return default

    return int(value)


def get_required_env(name: str) -> str:
    """读取必填环境变量。"""
    value = os.getenv(name)

    if value is None or value == "":
        raise RuntimeError(f"环境变量 {name} 未配置")

    return value


@dataclass(frozen=True)
class Settings:
    # 应用基础配置：控制服务名称、监听地址和端口。
    app_name: str = os.getenv("APP_NAME", "simplees")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = get_int_env("APP_PORT", 8000)

    # 数据库连接地址，当前项目要求使用 MySQL。
    database_url: str = get_required_env("DATABASE_URL")

    # 数据库连接池配置。
    # pool_size 表示连接池长期保留的连接数。
    # max_overflow 表示连接池不够用时，最多额外临时创建多少个连接。
    # pool_timeout 表示获取连接最多等待多少秒。
    # pool_recycle 表示连接最多复用多少秒后回收重建。
    db_pool_size: int = get_int_env("DB_POOL_SIZE", 5)
    db_max_overflow: int = get_int_env("DB_MAX_OVERFLOW", 10)
    db_pool_timeout_seconds: int = get_int_env("DB_POOL_TIMEOUT_SECONDS", 30)
    db_pool_recycle_seconds: int = get_int_env("DB_POOL_RECYCLE_SECONDS", 280)

    # Elasticsearch 连接配置。
    # 商品搜索时会通过这些配置连接 ES 并查询商品索引。
    es_host: str = os.getenv("ES_HOST", "http://127.0.0.1:9200")
    es_username: str = os.getenv("ES_USERNAME", "")
    es_password: str = os.getenv("ES_PASSWORD", "")
    es_product_index: str = os.getenv("ES_PRODUCT_INDEX", "product_search")
    es_request_timeout_seconds: int = get_int_env("ES_REQUEST_TIMEOUT_SECONDS", 5)

    # Canal 连接配置。
    # Canal Consumer 作为独立进程运行，消费 MySQL binlog 后同步 ES。
    canal_host: str = os.getenv("CANAL_HOST", "127.0.0.1")
    canal_port: int = get_int_env("CANAL_PORT", 11111)
    canal_destination: str = os.getenv("CANAL_DESTINATION", "canales")
    canal_filter: str = os.getenv("CANAL_FILTER", r"simplees\..*")
    canal_client_id: str = os.getenv("CANAL_CLIENT_ID", "1001")
    canal_username: str = os.getenv("CANAL_USERNAME", "")
    canal_password: str = os.getenv("CANAL_PASSWORD", "")
    canal_database: str = os.getenv("CANAL_DATABASE", "simplees")
    canal_batch_size: int = get_int_env("CANAL_BATCH_SIZE", 100)
    canal_empty_sleep_seconds: int = get_int_env("CANAL_EMPTY_SLEEP_SECONDS", 1)

    # 搜索分页配置。
    # default 表示用户没传 size 时默认返回多少条，max 表示最多允许返回多少条。
    search_default_page_size: int = get_int_env("SEARCH_DEFAULT_PAGE_SIZE", 10)
    search_max_page_size: int = get_int_env("SEARCH_MAX_PAGE_SIZE", 50)


# 全局配置对象。
# 后面其他文件通过 from app.config import settings 来使用这些配置。
settings = Settings()

# 使用案例说明
# from app.config import settings
#
# print(settings.database_url)
# print(settings.es_host)
