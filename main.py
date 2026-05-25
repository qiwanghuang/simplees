from fastapi import FastAPI

from app.config import settings
from app.routes import router


# 创建 FastAPI 应用实例。
# title 会显示在接口文档里。
app = FastAPI(
    title=settings.app_name,
)

# 把商品相关路由挂到主应用上。
app.include_router(router)


@app.get("/")
def root():
    """健康检查接口。"""
    return {
        "message": "simplees is running",
    }