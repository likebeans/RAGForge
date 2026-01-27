"""角色管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.models import Role, User
from app.api.deps import get_current_admin_user, get_current_user

router = APIRouter()


@router.get("", response_model=list[RoleResponse])
async def get_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取角色列表"""
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("", response_model=RoleResponse)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """创建角色（管理员）"""
    result = await db.execute(select(Role).where(Role.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists"
        )
    
    role = Role(
        name=data.name,
        display_name=data.display_name or data.name,
        description=data.description
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """更新角色（管理员）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if data.display_name is not None:
        role.display_name = data.display_name
    if data.description is not None:
        role.description = data.description
    
    await db.commit()
    await db.refresh(role)
    
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """删除角色（管理员）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    await db.delete(role)
    await db.commit()
    
    return {"message": "Role deleted"}
