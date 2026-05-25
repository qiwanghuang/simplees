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


@dataclass(frozen=True)
class Settings:
    # 应用基础配置：控制服务名称、监听地址和端口。
    app_name: str = os.getenv("APP_NAME", "simplees")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = get_int_env("APP_PORT", 8000)

    # 数据库连接地址。
    # 当前默认使用 SQLite，以后切换 MySQL/PostgreSQL 时主要改这里。
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/simplees.db")

    # Elasticsearch 连接配置。
    # 商品搜索时会通过这些配置连接 ES 并查询商品索引。
    es_host: str = os.getenv("ES_HOST", "http://127.0.0.1:9200")
    es_username: str = os.getenv("ES_USERNAME", "")
    es_password: str = os.getenv("ES_PASSWORD", "")
    es_product_index: str = os.getenv("ES_PRODUCT_INDEX", "product_search")
    es_request_timeout_seconds: int = get_int_env("ES_REQUEST_TIMEOUT_SECONDS", 5)

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
