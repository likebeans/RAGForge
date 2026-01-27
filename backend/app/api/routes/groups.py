"""部门管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse
from app.models import Group, User
from app.api.deps import get_current_admin_user, get_current_user

router = APIRouter()


@router.get("", response_model=list[GroupResponse])
async def get_groups(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取部门列表"""
    result = await db.execute(select(Group))
    groups = result.scalars().all()
    return [GroupResponse.model_validate(g) for g in groups]


@router.post("", response_model=GroupResponse)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """创建部门（管理员）"""
    result = await db.execute(select(Group).where(Group.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group already exists"
        )
    
    group = Group(
        name=data.name,
        display_name=data.display_name or data.name,
        description=data.description,
        parent_id=data.parent_id
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return GroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """更新部门（管理员）"""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if data.display_name is not None:
        group.display_name = data.display_name
    if data.description is not None:
        group.description = data.description
    if data.parent_id is not None:
        group.parent_id = data.parent_id
    
    await db.commit()
    await db.refresh(group)
    
    return GroupResponse.model_validate(group)


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """删除部门（管理员）"""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    await db.delete(group)
    await db.commit()
    
    return {"message": "Group deleted"}
