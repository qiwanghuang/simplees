# DELETE /api/products/{product_id}

## 接口身份

- 方法：`DELETE`
- 路径：`/api/products/{product_id}`
- 入口：`app.routes.delete_product_api`
- 主要用途：软删除商品。

## 请求结构

路径参数：

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | `str` | 商品 UUID |

无请求体。

## 响应结构

成功返回：

```json
{
  "message": "删除成功"
}
```

## 当前业务流程

1. FastAPI 路由接收 `product_id`。
2. 调用 `app.services.delete_product` 查询未删除商品。
3. 如果商品不存在或已删除，返回 `404`。
4. 如果商品存在，将 MySQL 中的 `products.status` 更新为 `deleted`，同时刷新 `updated_at`。
5. 返回删除成功消息。
6. ES 不再由接口内同步删除，而是由 Canal Consumer 消费 MySQL binlog 后异步删除或刷新 ES 文档。

## 数据读写

- 读取：`products`
- 写入：`products.status`、`products.updated_at`
- ES：接口请求链路不直接写 ES

## 异步事件与一致性

该接口提交 MySQL 后会产生 `products` 表 UPDATE binlog。`app.canal_consumer` 捕获变更后调用 `sync_product_by_id_to_es`。当查询到商品状态为 `deleted` 时，`app.es_sync.sync_product_to_es` 会删除对应 ES 文档。

因此接口返回成功只代表 MySQL 软删除成功；ES 搜索结果是最终一致，存在短暂延迟。

## 错误行为

| 场景 | 结果 |
|---|---|
| 商品不存在或已删除 | `404`，`detail="商品不存在"` |
| ES 不可用 | 不影响该接口返回；Canal Consumer 后续同步会失败并 rollback Canal batch |

## 最近变更

- 改为 Canal 异步同步 ES：删除接口内的 `sync_product_by_id_to_es` 调用，避免业务接口直接写 ES。
