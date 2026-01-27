"""认证服务"""

from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.models import User, Role, Group
from app.config import get_settings

settings = get_settings()


class AuthService:
    """认证服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate(self, username: str, password: str) -> User | None:
        """验证用户名密码"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    async def register(
        self,
        username: str,
        password: str,
        email: str | None = None,
        display_name: str | None = None
    ) -> User:
        """注册新用户"""
        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            display_name=display_name or username,
            clearance="public",
            is_admin=False
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    def create_token(self, user: User) -> dict:
        """创建 Token 响应"""
        expires_delta = timedelta(days=settings.jwt_expire_days)
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=expires_delta
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(expires_delta.total_seconds()),
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "roles": [r.name for r in user.roles],
                "groups": [g.name for g in user.groups],
                "clearance": user.clearance,
                "is_admin": user.is_admin
            }
        }
    
    async def get_user_by_id(self, user_id: str) -> User | None:
        """通过 ID 获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
