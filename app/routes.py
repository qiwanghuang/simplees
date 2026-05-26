from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.es_sync import sync_product_by_id_to_es
from app.schemas import MessageResponse, ProductDetail, ProductSearchResponse, ProductUpdateRequest
from app.services import delete_product, get_product_by_id, list_products, normalize_size, search_products, update_product


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductSearchResponse)
def list_product_api(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, description="每页数量"),
    db: Session = Depends(get_db),
):
    """商品分页列表接口：直接查询 SQLite，不走 ES。"""

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


@router.get("/search", response_model=ProductSearchResponse)
def search_product_api(
    q: str = Query(..., min_length=1, description="搜索关键词，可输入商品名、品牌名或类目名"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, description="每页数量"),
    db: Session = Depends(get_db),
):
    """商品搜索接口：先查 ES 获取商品 UUID，再回查 SQLite 返回商品详情。"""

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


@router.get("/{product_id}", response_model=ProductDetail)
def get_product_api(
    product_id: str,
    db: Session = Depends(get_db),
):
    """商品详情接口：根据商品 UUID 直接查询 SQLite。"""

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


@router.put("/{product_id}", response_model=ProductDetail)
def update_product_api(
    product_id: str,
    request: ProductUpdateRequest,
    db: Session = Depends(get_db),
):
    """更新商品接口：先更新 SQLite，成功后同步刷新 ES。"""

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

    # 数据库更新成功后，按商品 ID 重新查询最新数据并覆盖 ES 文档。
    sync_product_by_id_to_es(
        db=db,
        product_id=product_id,
    )

    return product


@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product_api(
    product_id: str,
    db: Session = Depends(get_db),
):
    """删除商品接口：先软删除 SQLite，成功后删除 ES 文档。"""

    deleted = delete_product(
        db=db,
        product_id=product_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="商品不存在",
        )

    # delete_product 会把商品状态改成 deleted。
    # sync_product_by_id_to_es 重新查到 deleted 状态后，会删除 ES 文档。
    sync_product_by_id_to_es(
        db=db,
        product_id=product_id,
    )

    return {
        "message": "删除成功",
    }
