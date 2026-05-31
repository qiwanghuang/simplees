# GET /api/brands

## 接口身份

- 方法：`GET`
- 路径：`/api/brands`
- 入口：`app.routes.list_brand_api`
- 主要用途：提供品牌下拉框选项。

## 请求结构

无路径参数、查询参数和请求体。

## 响应结构

返回 `BrandOption` 数组：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 品牌 UUID |
| `name` | `str` | 品牌名称 |

## 当前业务流程

1. FastAPI 路由接收请求。
2. 调用 `app.services.list_brands` 查询 MySQL。
3. 只返回 `status = active` 的品牌。
4. 按 `Brand.name` 升序返回。

## 数据读写

- 读取：`brands`
- 写入：无
- ES：不访问

## 错误行为

当前没有业务级错误处理；数据库异常会按框架默认异常返回。

## 最近变更

- 新增品牌选项接口，用于商品新增/编辑弹窗的品牌下拉框。
