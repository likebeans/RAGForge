"""用户服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.models import User, Role, Group


class UserService:
    """用户服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """获取用户列表"""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_user_by_id(self, user_id: str) -> User | None:
        """通过 ID 获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> User | None:
        """通过用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        username: str,
        password: str,
        email: str | None = None,
        display_name: str | None = None,
        clearance: str = "public",
        is_admin: bool = False,
        role_ids: list[str] = None,
        group_ids: list[str] = None
    ) -> User:
        """创建用户"""
        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            display_name=display_name or username,
            clearance=clearance,
            is_admin=is_admin
        )
        
        if role_ids:
            roles = await self._get_roles_by_ids(role_ids)
            user.roles = roles
        
        if group_ids:
            groups = await self._get_groups_by_ids(group_ids)
            user.groups = groups
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_user(self, user: User, **kwargs) -> User:
        """更新用户"""
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def delete_user(self, user: User) -> None:
        """删除用户"""
        await self.db.delete(user)
        await self.db.commit()
    
    async def set_user_roles(self, user: User, role_ids: list[str]) -> User:
        """设置用户角色"""
        roles = await self._get_roles_by_ids(role_ids)
        user.roles = roles
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def set_user_groups(self, user: User, group_ids: list[str]) -> User:
        """设置用户部门"""
        groups = await self._get_groups_by_ids(group_ids)
        user.groups = groups
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def _get_roles_by_ids(self, role_ids: list[str]) -> list[Role]:
        """通过 ID 列表获取角色"""
        result = await self.db.execute(
            select(Role).where(Role.id.in_(role_ids))
        )
        return list(result.scalars().all())
    
    async def _get_groups_by_ids(self, group_ids: list[str]) -> list[Group]:
        """通过 ID 列表获取部门"""
        result = await self.db.execute(
            select(Group).where(Group.id.in_(group_ids))
        )
        return list(result.scalars().all())
    
    async def get_roles(self) -> list[Role]:
        """获取所有角色"""
        result = await self.db.execute(select(Role))
        return list(result.scalars().all())
    
    async def get_groups(self) -> list[Group]:
        """获取所有部门"""
        result = await self.db.execute(select(Group))
        return list(result.scalars().all())
    
    async def create_role(self, name: str, display_name: str | None = None, description: str | None = None) -> Role:
        """创建角色"""
        role = Role(name=name, display_name=display_name or name, description=description)
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role
    
    async def create_group(self, name: str, display_name: str | None = None, description: str | None = None, parent_id: str | None = None) -> Group:
        """创建部门"""
        group = Group(name=name, display_name=display_name or name, description=description, parent_id=parent_id)
        self.db.add(group)
        await self.db.commit()
        await self.db.refresh(group)
        return group
