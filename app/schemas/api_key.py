"""API Key 相关的请求/响应模型"""

from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """创建 API Key 请求"""
    name: str = Field(..., max_length=255, description="Key 名称（用于识别用途）")
    expires_at: datetime | None = Field(default=None, description="过期时间，空表示永不过期")
    rate_limit_per_minute: int | None = Field(default=None, ge=1, description="独立限流配置")


class APIKeyInfo(BaseModel):
    """API Key 信息（不含完整 Key）"""
    id: str
    name: str
    prefix: str            # Key 前缀，用于识别
    revoked: bool          # 是否已撤销
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeySecret(APIKeyInfo):
    """API Key 创建响应（含完整 Key，仅创建时返回一次）"""
    api_key: str  # 完整的 API Key，仅此时可见


class APIKeyUpdate(BaseModel):
    """更新 API Key 请求"""
    name: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
