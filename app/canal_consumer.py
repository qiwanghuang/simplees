import logging
import time
from dataclasses import dataclass, field

from canal.client import Client
from canal.protocol import EntryProtocol_pb2

from app.config import settings
from app.database import SessionLocal
from app.es_sync import (
    sync_product_by_id_to_es,
    sync_products_by_brand_id_to_es,
    sync_products_by_category_id_to_es,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


@dataclass
class SyncPlan:
    """一批 Canal 消息对应的 ES 同步计划。"""

    product_ids: set[str] = field(default_factory=set)
    brand_ids: set[str] = field(default_factory=set)
    category_ids: set[str] = field(default_factory=set)

    def is_empty(self) -> bool:
        """判断当前批次是否没有需要同步的业务数据。"""

        return not self.product_ids and not self.brand_ids and not self.category_ids


def enum_name(enum_type, value) -> str:
    """把 protobuf 枚举值转换成可读字符串。"""

    try:
        return enum_type.Name(value)
    except ValueError:
        return str(value)


def columns_to_dict(columns) -> dict[str, str]:
    """把 Canal 的字段列表转换成字典。"""

    return {
        column.name: column.value
        for column in columns
    }


def get_row_id(row_data, event_type: str) -> str | None:
    """从一行变更数据里取主键 id。"""

    if event_type == "DELETE":
        values = columns_to_dict(row_data.beforeColumns)
    else:
        values = columns_to_dict(row_data.afterColumns)

    return values.get("id")


def build_sync_plan(entries) -> SyncPlan:
    """把 Canal 原始消息转换成 ES 同步计划。"""

    plan = SyncPlan()

    for entry in entries:
        if entry.entryType in (
            EntryProtocol_pb2.EntryType.TRANSACTIONBEGIN,
            EntryProtocol_pb2.EntryType.TRANSACTIONEND,
        ):
            continue

        header = entry.header

        if header.schemaName != settings.canal_database:
            continue

        table_name = header.tableName

        if table_name not in {"products", "brands", "categories"}:
            continue

        row_change = EntryProtocol_pb2.RowChange()
        row_change.MergeFromString(entry.storeValue)

        event_type = enum_name(
            EntryProtocol_pb2.EventType,
            row_change.eventType,
        )

        for row_data in row_change.rowDatas:
            row_id = get_row_id(
                row_data=row_data,
                event_type=event_type,
            )

            if not row_id:
                logger.warning(
                    "跳过没有主键 id 的 Canal 变更：table=%s event=%s",
                    table_name,
                    event_type,
                )
                continue

            if table_name == "products":
                plan.product_ids.add(row_id)

            if table_name == "brands":
                plan.brand_ids.add(row_id)

            if table_name == "categories":
                plan.category_ids.add(row_id)

            logger.info(
                "捕获 Canal 变更：schema=%s table=%s event=%s id=%s",
                header.schemaName,
                table_name,
                event_type,
                row_id,
            )

    return plan


def apply_sync_plan(plan: SyncPlan) -> None:
    """根据同步计划刷新 ES。"""

    db = SessionLocal()

    try:
        for product_id in sorted(plan.product_ids):
            sync_product_by_id_to_es(
                db=db,
                product_id=product_id,
            )
            logger.info("已同步商品到 ES：product_id=%s", product_id)

        for brand_id in sorted(plan.brand_ids):
            count = sync_products_by_brand_id_to_es(
                db=db,
                brand_id=brand_id,
            )
            logger.info(
                "已按品牌刷新 ES：brand_id=%s product_count=%s",
                brand_id,
                count,
            )

        for category_id in sorted(plan.category_ids):
            count = sync_products_by_category_id_to_es(
                db=db,
                category_id=category_id,
            )
            logger.info(
                "已按类目刷新 ES：category_id=%s product_count=%s",
                category_id,
                count,
            )

    finally:
        db.close()


def create_canal_client() -> Client:
    """创建 Canal 客户端并订阅指定 destination。"""

    client = Client()

    logger.info(
        "连接 Canal：host=%s port=%s destination=%s filter=%s",
        settings.canal_host,
        settings.canal_port,
        settings.canal_destination,
        settings.canal_filter,
    )

    client.connect(
        host=settings.canal_host,
        port=settings.canal_port,
    )

    client.check_valid(
        username=settings.canal_username.encode("utf-8"),
        password=settings.canal_password.encode("utf-8"),
    )

    client.subscribe(
        client_id=settings.canal_client_id.encode("utf-8"),
        destination=settings.canal_destination.encode("utf-8"),
        filter=settings.canal_filter.encode("utf-8"),
    )

    logger.info("Canal 订阅成功")

    return client


def consume_forever() -> None:
    """持续消费 Canal binlog 消息，并把变更同步到 ES。"""

    client = create_canal_client()

    try:
        while True:
            message = client.get_without_ack(
                batch_size=settings.canal_batch_size,
            )

            batch_id = message["id"]
            entries = message["entries"]

            if not entries:
                time.sleep(settings.canal_empty_sleep_seconds)
                continue

            try:
                plan = build_sync_plan(entries)

                if plan.is_empty():
                    logger.info(
                        "当前 Canal 批次没有需要同步的业务表变更：batch_id=%s entries=%s",
                        batch_id,
                        len(entries),
                    )
                else:
                    apply_sync_plan(plan)

                client.ack(batch_id)

                logger.info(
                    "Canal 批次处理成功并 ack：batch_id=%s entries=%s",
                    batch_id,
                    len(entries),
                )

            except Exception:
                logger.exception(
                    "Canal 批次同步失败，执行 rollback：batch_id=%s",
                    batch_id,
                )
                client.rollback(batch_id)
                time.sleep(3)

    finally:
        client.disconnect()


if __name__ == "__main__":
    consume_forever()