# simplees

`simplees` 是一个用于学习 MySQL、Elasticsearch 和 Canal 的商品搜索示例项目。

项目以 MySQL 作为业务数据源，Elasticsearch 作为商品搜索索引，Canal 监听 MySQL binlog 后投递到 RabbitMQ，Python Consumer 再消费 RabbitMQ 消息并异步同步 ES。页面端提供商品列表、搜索、添加、编辑和删除能力。

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- MySQL
- Elasticsearch 8.x
- Canal
- RabbitMQ
- 原生 HTML/CSS/JavaScript

## 核心流程

```text
页面操作商品
  -> FastAPI 接口
  -> 写入 MySQL
  -> MySQL 产生 binlog
  -> Canal Server 监听 binlog
  -> Canal Server 投递消息到 RabbitMQ
  -> app.rabbitmq_consumer 消费 RabbitMQ 消息
  -> 同步商品文档到 Elasticsearch
  -> 搜索接口查询 Elasticsearch
```

普通商品列表直接查询 MySQL；商品搜索先查询 ES 获取商品 ID，再回查 MySQL 返回完整商品数据。

## 目录说明

```text
.
├── app/
│   ├── static/              # 前端页面资源
│   ├── config.py            # 环境变量配置
│   ├── database.py          # SQLAlchemy 数据库连接
│   ├── models.py            # ORM 模型
│   ├── routes.py            # FastAPI 路由
│   ├── services.py          # 业务逻辑
│   ├── es_index.py          # ES 索引创建
│   ├── es_sync.py           # ES 全量/单条同步工具
│   ├── canal_consumer.py    # 旧版 Canal TCP 消费进程，当前主流程不使用
│   ├── canal_debug_consumer.py # Canal TCP 调试消费进程
│   └── rabbitmq_consumer.py # RabbitMQ 增量消费进程
├── docs/api-logic/          # 接口逻辑说明文档
├── main.py                  # FastAPI 入口
├── start.sh                 # 本地启动脚本
├── requirements.txt         # Python 依赖
└── .env.example             # 环境变量示例
```

## 环境准备

先创建虚拟环境并安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

复制环境变量模板：

```bash
cp .env.example .env
```

然后根据本机环境修改 `.env`：

```env
DATABASE_URL=mysql+pymysql://simplees:change_me@127.0.0.1:3306/simplees?charset=utf8mb4
ES_HOST=http://127.0.0.1:9200
CANAL_HOST=127.0.0.1
CANAL_PORT=11111
CANAL_DESTINATION=canales
CANAL_FILTER=simplees\..*
CANAL_DATABASE=simplees
RABBITMQ_HOST=127.0.0.1
RABBITMQ_PORT=5672
RABBITMQ_VHOST=simplees
RABBITMQ_USERNAME=simplees
RABBITMQ_PASSWORD=simplees123
RABBITMQ_QUEUE=simplees.canal.queue
```

注意：`.env` 只放本地配置，不要提交到仓库。

## MySQL 要求

Canal 依赖 MySQL binlog，MySQL 需要开启以下配置：

```sql
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW VARIABLES LIKE 'binlog_row_image';
SHOW VARIABLES LIKE 'server_id';
```

期望结果：

- `log_bin = ON`
- `binlog_format = ROW`
- `binlog_row_image = FULL`
- `server_id` 不能为 `0`

Canal 读取 MySQL binlog 还需要一个有复制权限的用户：

```sql
CREATE USER IF NOT EXISTS 'canal'@'%' IDENTIFIED BY '123456';
GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'canal'@'%';
FLUSH PRIVILEGES;
```

## 初始化数据

创建 MySQL 表：

```bash
python -m app.init_db
```

写入测试数据：

```bash
python -m app.seed_data
```

创建 ES 索引：

```bash
python -m app.es_index
```

首次使用或需要修复 ES 数据时，可以执行全量同步：

```bash
python -m app.es_sync
```

## 启动服务

启动 FastAPI：

```bash
./start.sh
```

默认访问地址：

```text
http://127.0.0.1:8000
```

商品管理页面：

```text
http://127.0.0.1:8000/products-page
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 启动 RabbitMQ 增量同步

FastAPI 服务只负责写 MySQL，不会在接口里直接写 ES。

当前增量同步链路是：

```text
MySQL -> Canal -> RabbitMQ -> app.rabbitmq_consumer -> ES
```

需要单独启动 RabbitMQ Consumer：

```bash
python -m app.rabbitmq_consumer
```

调试 Canal TCP 原始变更时，可以使用旧的调试脚本：

```bash
python -m app.canal_debug_consumer
```

旧版 Canal TCP 消费进程仍保留在项目中，但当前主流程不使用：

```bash
python -m app.canal_consumer
```

如果商品添加、修改、删除后 ES 没有变化，优先检查：

1. Canal Server 是否正在运行。
2. RabbitMQ 是否正在运行。
3. `python -m app.rabbitmq_consumer` 是否正在运行。
4. RabbitMQ 队列 `simplees.canal.queue` 是否有消息堆积。
5. MySQL binlog 是否开启。
6. `.env` 里的 `CANAL_DATABASE`、`RABBITMQ_HOST`、`RABBITMQ_VHOST`、`RABBITMQ_QUEUE` 是否正确。

## 主要接口

| 方法 | 地址 | 说明 |
| --- | --- | --- |
| `GET` | `/api/products` | 商品分页列表，直接查询 MySQL |
| `POST` | `/api/products` | 添加商品，只写 MySQL |
| `GET` | `/api/products/search` | 商品搜索，先查 ES 再回查 MySQL |
| `GET` | `/api/products/{product_id}` | 商品详情 |
| `PUT` | `/api/products/{product_id}` | 修改商品，只写 MySQL |
| `DELETE` | `/api/products/{product_id}` | 删除商品，只写 MySQL，ES 由 RabbitMQ Consumer 异步同步 |
| `GET` | `/api/brands` | 品牌下拉选项 |
| `GET` | `/api/categories` | 类目下拉选项 |

## 常用命令

安装依赖并启动：

```bash
INSTALL_DEPS=1 ./start.sh
```

关闭热重载启动：

```bash
RELOAD=0 ./start.sh
```

指定端口启动：

```bash
APP_PORT=8001 ./start.sh
```

重新创建 ES 索引并全量同步：

```bash
python -m app.es_index
python -m app.es_sync
```

## 说明

- MySQL 是业务数据源，ES 只是搜索索引。
- 接口写入成功只代表 MySQL 已成功提交。
- ES 是否更新取决于 Canal Server、RabbitMQ 和 `app.rabbitmq_consumer` 是否正常运行。
- 事务回滚不会产生最终提交的 binlog，因此 Canal 不会同步失败回滚的数据。
- `.env.example` 可以提交，`.env` 不应该提交。
