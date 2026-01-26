"""
模型配置 Pydantic Schemas

定义 API 请求/响应模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConfigCreate(BaseModel):
    """创建模型配置请求"""
    config_type: str = Field(
        ...,
        description="配置类型: embedding/llm/rerank"
    )
    provider: str = Field(
        ...,
        description="模型提供商: openai/ollama/siliconflow/qwen/deepseek/zhipu/cohere"
    )
    model: Optional[str] = Field(
        None,
        description="模型名称"
    )
    api_key: str = Field(
        ...,
        description="API Key（加密存储）"
    )
    base_url: Optional[str] = Field(
        None,
        description="API Base URL（可选，用于自托管服务如 Ollama）"
    )
    is_active: bool = Field(
        True,
        description="是否启用"
    )


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求"""
    provider: Optional[str] = Field(
        None,
        description="模型提供商"
    )
    model: Optional[str] = Field(
        None,
        description="模型名称"
    )
    api_key: Optional[str] = Field(
        None,
        description="API Key"
    )
    base_url: Optional[str] = Field(
        None,
        description="API Base URL"
    )
    is_active: Optional[bool] = Field(
        None,
        description="是否启用"
    )


class ModelConfigResponse(BaseModel):
    """模型配置响应（不返回 api_key）"""
    id: str
    tenant_id: str
    config_type: str
    provider: str
    model: Optional[str]
    base_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelConfigResponseWithKey(BaseModel):
    """模型配置响应（返回 api_key，仅创建时使用）"""
    id: str
    tenant_id: str
    config_type: str
    provider: str
    model: Optional[str]
    api_key: str  # 仅创建时返回
    base_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelConfigListResponse(BaseModel):
    """模型配置列表响应"""
    items: list[ModelConfigResponse]
    total: int


class TenantModelConfigCheck(BaseModel):
    """检查租户模型配置是否完整"""
    embedding_configured: bool
    llm_configured: bool
    rerank_configured: bool
    missing_configs: list[str]

