from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import router


# 创建 FastAPI 应用实例。
# title 会显示在接口文档里。
app = FastAPI(
    title=settings.app_name,
)

# 挂载静态文件目录。
# 后面简单 HTML 页面会放在 app/static 下面。
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 把商品相关路由挂到主应用上。
app.include_router(router)


@app.get("/")
def root():
    """健康检查接口。"""
    return {
        "message": "simplees is running",
    }


@app.get("/products-page")
def products_page():
    """商品列表演示页面。"""
    return FileResponse("app/static/index.html")
