from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProductDetail, ProductSearchResponse
from app.services import get_product_by_id, normalize_size, search_products


router = APIRouter(prefix="/api/products", tags=["products"])


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