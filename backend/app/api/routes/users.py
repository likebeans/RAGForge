"""用户管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserDetail, UserRolesUpdate, UserGroupsUpdate, RoleBasic, GroupBasic
from app.services.user_service import UserService
from app.api.deps import get_current_admin_user
from app.models import User

router = APIRouter()


@router.get("", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """获取用户列表（管理员）"""
    service = UserService(db)
    users = await service.get_users(skip=skip, limit=limit)
    
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            email=u.email,
            clearance=u.clearance,
            is_active=u.is_active,
            is_admin=u.is_admin,
            roles=[r.name for r in u.roles],
            groups=[g.name for g in u.groups],
            created_at=u.created_at
        )
        for u in users
    ]


@router.post("", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """创建用户（管理员）"""
    service = UserService(db)
    
    existing = await service.get_user_by_username(data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    user = await service.create_user(
        username=data.username,
        password=data.password,
        email=data.email,
        display_name=data.display_name,
        clearance=data.clearance,
        is_admin=data.is_admin,
        role_ids=data.role_ids,
        group_ids=data.group_ids
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        clearance=user.clearance,
        is_active=user.is_active,
        is_admin=user.is_admin,
        roles=[r.name for r in user.roles],
        groups=[g.name for g in user.groups],
        created_at=user.created_at
    )


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """获取用户详情（管理员）"""
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserDetail(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        clearance=user.clearance,
        is_active=user.is_active,
        is_admin=user.is_admin,
        roles=[RoleBasic(id=r.id, name=r.name, display_name=r.display_name) for r in user.roles],
        groups=[GroupBasic(id=g.id, name=g.name, display_name=g.display_name) for g in user.groups],
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """更新用户（管理员）"""
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = await service.update_user(
        user,
        email=data.email,
        display_name=data.display_name,
        clearance=data.clearance,
        is_active=data.is_active,
        is_admin=data.is_admin
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        clearance=user.clearance,
        is_active=user.is_active,
        is_admin=user.is_admin,
        roles=[r.name for r in user.roles],
        groups=[g.name for g in user.groups],
        created_at=user.created_at
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """删除用户（管理员）"""
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await service.delete_user(user)
    return {"message": "User deleted"}


@router.put("/{user_id}/roles")
async def set_user_roles(
    user_id: str,
    data: UserRolesUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """设置用户角色（管理员）"""
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = await service.set_user_roles(user, data.role_ids)
    
    return {
        "message": "Roles updated",
        "roles": [r.name for r in user.roles]
    }


@router.put("/{user_id}/groups")
async def set_user_groups(
    user_id: str,
    data: UserGroupsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """设置用户部门（管理员）"""
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = await service.set_user_groups(user, data.group_ids)
    
    return {
        "message": "Groups updated",
        "groups": [g.name for g in user.groups]
    }
