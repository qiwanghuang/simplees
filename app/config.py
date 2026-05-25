import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or value == "":
        return default

    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "simplees")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = get_int_env("APP_PORT", 8000)

    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "./data/simplees.db")

    es_host: str = os.getenv("ES_HOST", "http://127.0.0.1:9200")
    es_username: str = os.getenv("ES_USERNAME", "")
    es_password: str = os.getenv("ES_PASSWORD", "")
    es_product_index: str = os.getenv("ES_PRODUCT_INDEX", "product_search")
    es_request_timeout_seconds: int = get_int_env("ES_REQUEST_TIMEOUT_SECONDS", 5)

    search_default_page_size: int = get_int_env("SEARCH_DEFAULT_PAGE_SIZE", 10)
    search_max_page_size: int = get_int_env("SEARCH_MAX_PAGE_SIZE", 50)


settings = Settings()

# 使用案例说明
# from app.config import settings
#
# print(settings.sqlite_db_path)
# print(settings.es_host)