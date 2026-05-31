# PUT /api/products/{product_id}

## 接口身份

- 方法：`PUT`
- 路径：`/api/products/{product_id}`
- 入口：`app.routes.update_product_api`
- 主要用途：更新商品主数据。

## 请求结构

路径参数：

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `str` | 商品 UUID |

请求体：`ProductUpdateRequest`

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str` | 商品名称 |
| `description` | `str | None` | 商品描述 |
| `price` | `Decimal | None` | 商品价格 |
| `brand_id` | `str` | 品牌 UUID |
| `category_id` | `str` | 类目 UUID |
| `status` | `Literal["active", "inactive"]` | 商品状态，不允许通过该接口写入 `deleted` |

## 响应结构

成功返回：`ProductDetail`

包含商品基础字段、品牌信息、类目信息、创建时间和更新时间。

## 当前业务流程

1. FastAPI 路由接收 `product_id` 和 `ProductUpdateRequest`。
2. 调用 `app.services.update_product` 查询未删除商品。
3. 如果商品不存在或已删除，返回 `404`。
4. 如果商品存在，更新 MySQL 中的商品字段并提交事务。
5. 返回更新后的商品详情。
6. ES 不再由接口内同步刷新，而是由 Canal Consumer 消费 MySQL binlog 后异步同步。

## 数据读写

- 读取：`products`、`brands`、`categories`
- 写入：`products`
- ES：接口请求链路不直接写 ES

## 异步事件与一致性

该接口提交 MySQL 后会产生 binlog。`app.canal_consumer` 订阅 Canal destination，并在捕获 `products` 表变更后调用 `sync_product_by_id_to_es` 刷新 ES。

因此接口返回成功只代表 MySQL 更新成功；ES 搜索结果是最终一致，存在短暂延迟。

## 错误行为

| 场景 | 结果 |
|---|---|
| 商品不存在或已删除 | `404`，`detail="商品不存在"` |
| 请求体状态不是 `active` 或 `inactive` | FastAPI/Pydantic 校验失败 |
| ES 不可用 | 不影响该接口返回；Canal Consumer 后续同步会失败并 rollback Canal batch |

## 最近变更

- 改为 Canal 异步同步 ES：删除接口内的 `sync_product_by_id_to_es` 调用，避免业务接口直接写 ES。
