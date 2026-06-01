import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import pika
from sqlalchemy.orm import Session

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
class RabbitMQSyncPlan:
    """一条 Canal RabbitMQ 消息对应的 ES 同步计划。"""

    product_ids: set[str] = field(default_factory=set)
    brand_ids: set[str] = field(default_factory=set)
    category_ids: set[str] = field(default_factory=set)

    def is_empty(self) -> bool:
        return not self.product_ids and not self.brand_ids and not self.category_ids


def build_sync_plan(message: dict[str, Any]) -> RabbitMQSyncPlan:
    """把 Canal flatMessage JSON 转换成 ES 同步计划。"""

    plan = RabbitMQSyncPlan()

    if message.get("isDdl"):
        logger.info("跳过 DDL 消息：%s", message.get("sql"))
        return plan

    database = message.get("database")
    table = message.get("table")
    event_type = message.get("type")

    if database != settings.canal_database:
        logger.info("跳过非目标数据库消息：database=%s table=%s", database, table)
        return plan

    if table not in {"products", "brands", "categories"}:
        logger.info("跳过非业务表消息：database=%s table=%s", database, table)
        return plan

    rows = message.get("data") or []

    for row in rows:
        row_id = row.get("id")

        if not row_id:
            logger.warning(
                "跳过没有主键 id 的消息：database=%s table=%s type=%s",
                database,
                table,
                event_type,
            )
            continue

        if table == "products":
            plan.product_ids.add(row_id)

        if table == "brands":
            plan.brand_ids.add(row_id)

        if table == "categories":
            plan.category_ids.add(row_id)

        logger.info(
            "捕获 RabbitMQ Canal 消息：database=%s table=%s type=%s id=%s",
            database,
            table,
            event_type,
            row_id,
        )

    return plan


def apply_sync_plan(db: Session, plan: RabbitMQSyncPlan) -> None:
    """根据同步计划刷新 ES。"""

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
        logger.info("已按品牌刷新 ES：brand_id=%s product_count=%s", brand_id, count)

    for category_id in sorted(plan.category_ids):
        count = sync_products_by_category_id_to_es(
            db=db,
            category_id=category_id,
        )
        logger.info("已按类目刷新 ES：category_id=%s product_count=%s", category_id, count)


def create_connection() -> pika.BlockingConnection:
    """创建 RabbitMQ 连接。"""

    credentials = pika.PlainCredentials(
        username=settings.rabbitmq_username,
        password=settings.rabbitmq_password,
    )

    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        virtual_host=settings.rabbitmq_vhost,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=300,
    )

    logger.info(
        "连接 RabbitMQ：host=%s port=%s vhost=%s queue=%s",
        settings.rabbitmq_host,
        settings.rabbitmq_port,
        settings.rabbitmq_vhost,
        settings.rabbitmq_queue,
    )

    return pika.BlockingConnection(parameters)


def handle_message(channel, method, properties, body: bytes) -> None:
    """处理 RabbitMQ 投递的一条 Canal 消息。"""

    try:
        message = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.exception("RabbitMQ 消息不是合法 JSON，执行 ack 避免阻塞队列")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    db = SessionLocal()

    try:
        plan = build_sync_plan(message)

        if plan.is_empty():
            logger.info("当前消息没有需要同步的业务数据")
        else:
            apply_sync_plan(
                db=db,
                plan=plan,
            )

        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("RabbitMQ 消息处理成功并 ack：delivery_tag=%s", method.delivery_tag)

    except Exception:
        logger.exception(
            "RabbitMQ 消息处理失败，执行 nack 并重新入队：delivery_tag=%s",
            method.delivery_tag,
        )
        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )
        time.sleep(settings.rabbitmq_reconnect_seconds)

    finally:
        db.close()


def consume_forever() -> None:
    """持续消费 RabbitMQ 消息，并把变更同步到 ES。"""

    while True:
        connection = None

        try:
            connection = create_connection()
            channel = connection.channel()

            channel.basic_qos(
                prefetch_count=settings.rabbitmq_prefetch_count,
            )

            channel.basic_consume(
                queue=settings.rabbitmq_queue,
                on_message_callback=handle_message,
            )

            logger.info("RabbitMQ Consumer 已启动，等待 Canal 消息")
            channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("收到退出信号，停止 RabbitMQ Consumer")

            if connection and connection.is_open:
                connection.close()

            break

        except Exception:
            logger.exception(
                "RabbitMQ Consumer 异常，%s 秒后重连",
                settings.rabbitmq_reconnect_seconds,
            )

            if connection and connection.is_open:
                connection.close()

            time.sleep(settings.rabbitmq_reconnect_seconds)


if __name__ == "__main__":
    consume_forever()