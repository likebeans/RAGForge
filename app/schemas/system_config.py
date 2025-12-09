"""系统配置相关的请求/响应模型"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SystemConfigItem(BaseModel):
    """系统配置项"""
    key: str = Field(description="配置键名")
    value: Any = Field(description="配置值")
    description: str | None = Field(default=None, description="配置描述")
    updated_at: datetime = Field(description="最后更新时间")


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求"""
    value: Any = Field(..., description="配置值（将被 JSON 序列化存储）")
    description: str | None = Field(default=None, description="配置描述（可选）")


class SystemConfigListResponse(BaseModel):
    """系统配置列表响应"""
    items: list[SystemConfigItem]
    total: int


class SystemConfigResetResponse(BaseModel):
    """重置配置响应"""
    message: str
    reset_keys: list[str]
