"""部门相关 Schema"""

from datetime import datetime
from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    """创建部门请求"""
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str | None = None
    description: str | None = None
    parent_id: str | None = None


class GroupUpdate(BaseModel):
    """更新部门请求"""
    display_name: str | None = None
    description: str | None = None
    parent_id: str | None = None


class GroupResponse(BaseModel):
    """部门响应"""
    id: str
    name: str
    display_name: str | None
    description: str | None
    parent_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True
