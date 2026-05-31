from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BrandOption,
    CategoryOption,
    MessageResponse,
    ProductCreateRequest,
    ProductDetail,
    ProductSearchResponse,
    ProductUpdateRequest,
)
from app.services import (
    create_product,
    delete_product,
    get_product_by_id,
    list_brands,
    list_categories,
    list_products,
    normalize_size,
    search_products,
    update_product,
)


router = APIRouter()
product_router = APIRouter(prefix="/api/products", tags=["products"])
brand_router = APIRouter(prefix="/api/brands", tags=["brands"])
category_router = APIRouter(prefix="/api/categories", tags=["categories"])


@product_router.get("", response_model=ProductSearchResponse)
def list_product_api(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, description="每页数量"),
    db: Session = Depends(get_db),
):
    """商品分页列表接口：直接查询 MySQL，不走 ES。"""

    # 普通列表不是搜索场景，所以直接查数据库。
    # size 仍然要做上限控制，避免一次请求返回太多商品。
    normalized_size = normalize_size(size)

    products, total = list_products(
        db=db,
        page=page,
        size=normalized_size,
    )

    return {
        "items": products,
        "total": total,
        "page": page,
        "size": normalized_size,
    }


@product_router.post("", response_model=ProductDetail)
def create_product_api(
    request: ProductCreateRequest,
    db: Session = Depends(get_db),
):
    """创建商品接口：只写 MySQL，ES 由 Canal Consumer 异步同步。"""

    return create_product(
        db=db,
        request=request,
    )


@product_router.get("/search", response_model=ProductSearchResponse)
def search_product_api(
    q: str = Query(..., min_length=1, description="搜索关键词，可输入商品名、品牌名或类目名"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, description="每页数量"),
    db: Session = Depends(get_db),
):
    """商品搜索接口：先查 ES 获取商品 UUID，再回查 MySQL 返回商品详情。"""

    # normalize_size 会限制 size 最大不能超过 SEARCH_MAX_PAGE_SIZE。
    normalized_size = normalize_size(size)

    products, total = search_products(
        db=db,
        keyword=q,
        page=page,
        size=normalized_size,
    )

    return {
        "items": products,
        "total": total,
        "page": page,
        "size": normalized_size,
    }


@product_router.get("/{product_id}", response_model=ProductDetail)
def get_product_api(
    product_id: str,
    db: Session = Depends(get_db),
):
    """商品详情接口：根据商品 UUID 直接查询 MySQL。"""

    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="商品不存在",
        )

    return product


@product_router.put("/{product_id}", response_model=ProductDetail)
def update_product_api(
    product_id: str,
    request: ProductUpdateRequest,
    db: Session = Depends(get_db),
):
    """更新商品接口：只更新 MySQL，ES 由 Canal Consumer 异步同步。"""

    product = update_product(
        db=db,
        product_id=product_id,
        request=request,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="商品不存在",
        )

    return product


@product_router.delete("/{product_id}", response_model=MessageResponse)
def delete_product_api(
    product_id: str,
    db: Session = Depends(get_db),
):
    """删除商品接口：只软删除 MySQL，ES 由 Canal Consumer 异步同步。"""

    deleted = delete_product(
        db=db,
        product_id=product_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="商品不存在",
        )

    return {
        "message": "删除成功",
    }


@brand_router.get("", response_model=list[BrandOption])
def list_brand_api(
    db: Session = Depends(get_db),
):
    """品牌下拉选项接口。"""

    return list_brands(db=db)


@category_router.get("", response_model=list[CategoryOption])
def list_category_api(
    db: Session = Depends(get_db),
):
    """类目下拉选项接口。"""

    return list_categories(db=db)


router.include_router(product_router)
router.include_router(brand_router)
router.include_router(category_router)
