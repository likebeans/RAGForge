"""
管理员 Token Schemas

定义管理员 Token 的请求和响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminTokenCreate(BaseModel):
    """创建管理员 Token 请求"""
    name: str = Field(..., description="Token 名称，如'主管理员'、'运维团队'")
    description: str | None = Field(None, description="Token 描述/备注")
    expires_at: datetime | None = Field(None, description="过期时间（UTC），为空则永不过期")
    created_by: str | None = Field(None, description="创建者信息")


class AdminTokenResponse(BaseModel):
    """管理员 Token 响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    prefix: str  # 前12个字符，用于识别
    revoked: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    description: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class AdminTokenCreateResponse(BaseModel):
    """创建管理员 Token 响应（包含明文 Token）"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    prefix: str
    expires_at: datetime | None
    description: str | None
    created_at: datetime
    token: str  # 明文 Token，仅在创建时返回一次


class AdminTokenListResponse(BaseModel):
    """管理员 Token 列表响应"""
    items: list[AdminTokenResponse]
    total: int
    skip: int
    limit: int
