"""用户相关 Schema"""

from datetime import datetime
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)
    email: str | None = None
    display_name: str | None = None
    clearance: str = "public"
    is_admin: bool = False
    role_ids: list[str] = []
    group_ids: list[str] = []


class UserUpdate(BaseModel):
    """更新用户请求"""
    email: str | None = None
    display_name: str | None = None
    clearance: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None


class UserRolesUpdate(BaseModel):
    """更新用户角色"""
    role_ids: list[str]


class UserGroupsUpdate(BaseModel):
    """更新用户部门"""
    group_ids: list[str]


class RoleBasic(BaseModel):
    """角色基础信息"""
    id: str
    name: str
    display_name: str | None


class GroupBasic(BaseModel):
    """部门基础信息"""
    id: str
    name: str
    display_name: str | None


class UserResponse(BaseModel):
    """用户响应（列表）"""
    id: str
    username: str
    display_name: str | None
    email: str | None
    clearance: str
    is_active: bool
    is_admin: bool
    roles: list[str]
    groups: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetail(BaseModel):
    """用户详情响应"""
    id: str
    username: str
    display_name: str | None
    email: str | None
    clearance: str
    is_active: bool
    is_admin: bool
    roles: list[RoleBasic]
    groups: list[GroupBasic]
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
