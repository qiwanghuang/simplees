import os
import time
from datetime import datetime

from canal.client import Client
from canal.protocol import EntryProtocol_pb2


CANAL_HOST = os.getenv("CANAL_HOST", "127.0.0.1")
CANAL_PORT = int(os.getenv("CANAL_PORT", "11111"))
CANAL_DESTINATION = os.getenv("CANAL_DESTINATION", "canales")
CANAL_FILTER = os.getenv("CANAL_FILTER", r"simplees\..*")
CANAL_CLIENT_ID = os.getenv("CANAL_CLIENT_ID", "1001")

# 这是 Canal TCP 客户端认证，不是 MySQL 账号。
# 我们当前没有给 Canal Server 配 canal.user/canal.passwd，所以默认留空。
CANAL_USERNAME = os.getenv("CANAL_USERNAME", "")
CANAL_PASSWORD = os.getenv("CANAL_PASSWORD", "")


def enum_name(enum_type, value):
    try:
        return enum_type.Name(value)
    except ValueError:
        return str(value)


def columns_to_dict(columns):
    return {
        column.name: column.value
        for column in columns
    }


def print_changed_columns(before, after, after_columns):
    for column in after_columns:
        old_value = before.get(column.name)
        new_value = after.get(column.name)

        if column.updated or old_value != new_value:
            print(f"    {column.name}: {old_value!r} -> {new_value!r}")


def handle_entry(entry):
    entry_type = entry.entryType

    if entry_type in (
        EntryProtocol_pb2.EntryType.TRANSACTIONBEGIN,
        EntryProtocol_pb2.EntryType.TRANSACTIONEND,
    ):
        return

    row_change = EntryProtocol_pb2.RowChange()
    row_change.MergeFromString(entry.storeValue)

    header = entry.header
    event_type = enum_name(EntryProtocol_pb2.EventType, row_change.eventType)

    print()
    print("=" * 80)
    print(f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"schema: {header.schemaName}")
    print(f"table: {header.tableName}")
    print(f"event: {event_type}")
    print(f"binlog: {header.logfileName}:{header.logfileOffset}")
    print("=" * 80)

    for row_data in row_change.rowDatas:
        before = columns_to_dict(row_data.beforeColumns)
        after = columns_to_dict(row_data.afterColumns)

        if event_type == "INSERT":
            print("  INSERT values:")
            for column in row_data.afterColumns:
                print(f"    {column.name}: {column.value!r}")

        elif event_type == "DELETE":
            print("  DELETE values:")
            for column in row_data.beforeColumns:
                print(f"    {column.name}: {column.value!r}")

        else:
            print("  UPDATE changed columns:")
            print_changed_columns(before, after, row_data.afterColumns)


def main():
    client = Client()

    print(f"connect canal: {CANAL_HOST}:{CANAL_PORT}")
    print(f"destination: {CANAL_DESTINATION}")
    print(f"filter: {CANAL_FILTER}")

    client.connect(host=CANAL_HOST, port=CANAL_PORT)

    client.check_valid(
        username=CANAL_USERNAME.encode("utf-8"),
        password=CANAL_PASSWORD.encode("utf-8"),
    )

    client.subscribe(
        client_id=CANAL_CLIENT_ID.encode("utf-8"),
        destination=CANAL_DESTINATION.encode("utf-8"),
        filter=CANAL_FILTER.encode("utf-8"),
    )

    print("canal consumer started. waiting for binlog events...")

    try:
        while True:
            message = client.get(100)
            entries = message.get("entries", [])

            if not entries:
                time.sleep(1)
                continue

            for entry in entries:
                handle_entry(entry)

    except KeyboardInterrupt:
        print("consumer stopped by user")

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()