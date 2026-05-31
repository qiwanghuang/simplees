# POST /api/products

## 接口身份

- 方法：`POST`
- 路径：`/api/products`
- 入口：`app.routes.create_product_api`
- 主要用途：创建商品主数据。

## 请求结构

请求体：`ProductCreateRequest`

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str` | 商品名称 |
| `description` | `str | None` | 商品描述 |
| `price` | `Decimal | None` | 商品价格 |
| `brand_id` | `str` | 品牌 UUID |
| `category_id` | `str` | 类目 UUID |
| `status` | `Literal["active", "inactive"]` | 商品状态，默认 `active` |

## 响应结构

成功返回：`ProductDetail`

包含商品基础字段、品牌信息、类目信息、创建时间和更新时间。

## 当前业务流程

1. FastAPI 路由接收 `ProductCreateRequest`。
2. 调用 `app.services.create_product` 写入 MySQL `products` 表。
3. 提交成功后，根据新商品 UUID 查询商品详情。
4. 返回创建后的商品详情。
5. ES 不由接口内同步写入，而是由 Canal Consumer 消费 MySQL binlog 后异步同步。

## 数据读写

- 写入：`products`
- 读取：`products`、`brands`、`categories`
- ES：接口请求链路不直接写 ES

## 异步事件与一致性

该接口提交 MySQL 后会产生 `products` 表 INSERT binlog。`app.canal_consumer` 捕获变更后调用 `sync_product_by_id_to_es`，查询 MySQL 最新商品数据并写入 ES。

因此接口返回成功只代表 MySQL 创建成功；ES 搜索结果是最终一致，存在短暂延迟。

## 错误行为

| 场景 | 结果 |
|---|---|
| 请求体字段类型不合法 | FastAPI/Pydantic 校验失败 |
| `brand_id` 或 `category_id` 不存在 | MySQL 外键或提交阶段报错 |
| ES 不可用 | 不影响该接口返回；Canal Consumer 后续同步会失败并 rollback Canal batch |

## 最近变更

- 新增商品创建接口，用于前端添加商品弹窗。
