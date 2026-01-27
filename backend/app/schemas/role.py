"""角色相关 Schema"""

from datetime import datetime
from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str | None = None
    description: str | None = None


class RoleUpdate(BaseModel):
    """更新角色请求"""
    display_name: str | None = None
    description: str | None = None


class RoleResponse(BaseModel):
    """角色响应"""
    id: str
    name: str
    display_name: str | None
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True
