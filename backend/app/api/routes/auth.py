"""认证路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import UserLogin, UserRegister, Token
from app.schemas.user import UserDetail, RoleBasic, GroupBasic
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    auth_service = AuthService(db)
    user = await auth_service.authenticate(data.username, data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    return auth_service.create_token(user)


@router.post("/register", response_model=Token)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    auth_service = AuthService(db)
    
    existing = await auth_service.get_user_by_id(data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    user = await auth_service.register(
        username=data.username,
        password=data.password,
        email=data.email,
        display_name=data.display_name
    )
    
    return auth_service.create_token(user)


@router.get("/me", response_model=UserDetail)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserDetail(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        email=current_user.email,
        clearance=current_user.clearance,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        roles=[RoleBasic(id=r.id, name=r.name, display_name=r.display_name) for r in current_user.roles],
        groups=[GroupBasic(id=g.id, name=g.name, display_name=g.display_name) for g in current_user.groups],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
