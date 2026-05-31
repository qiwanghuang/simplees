# GET /api/categories

## 接口身份

- 方法：`GET`
- 路径：`/api/categories`
- 入口：`app.routes.list_category_api`
- 主要用途：提供类目下拉框选项。

## 请求结构

无路径参数、查询参数和请求体。

## 响应结构

返回 `CategoryOption` 数组：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 类目 UUID |
| `name` | `str` | 类目名称 |

## 当前业务流程

1. FastAPI 路由接收请求。
2. 调用 `app.services.list_categories` 查询 MySQL。
3. 只返回 `status = active` 的类目。
4. 按 `Category.name` 升序返回。

## 数据读写

- 读取：`categories`
- 写入：无
- ES：不访问

## 错误行为

当前没有业务级错误处理；数据库异常会按框架默认异常返回。

## 最近变更

- 新增类目选项接口，用于商品新增/编辑弹窗的类目下拉框。
