"""字典路由"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import DictItem, User
from app.schemas.dict_item import DictItemResponse

router = APIRouter()


@router.get("", response_model=dict[str, list[DictItemResponse]])
async def get_all_dicts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(DictItem).where(DictItem.is_active == True).order_by(DictItem.category, DictItem.sort_order))
    items = list(result.scalars().all())

    grouped: dict[str, list[DictItemResponse]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(DictItemResponse.model_validate(item))

    return grouped


@router.get("/{category}", response_model=list[DictItemResponse])
async def get_dict_by_category(
    category: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DictItem)
        .where(DictItem.category == category, DictItem.is_active == True)
        .order_by(DictItem.sort_order)
    )
    items = list(result.scalars().all())
    return [DictItemResponse.model_validate(i) for i in items]
