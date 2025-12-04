"""租户相关的请求/响应模型"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# 类型定义（用于验证）
TenantStatus = Literal["active", "disabled", "pending"]
TenantPlan = Literal["free", "standard", "enterprise"]
IsolationStrategy = Literal["partition", "collection", "auto"]


class TenantCreate(BaseModel):
    """创建租户请求"""
    name: str = Field(..., min_length=1, max_length=255, description="租户名称，全局唯一")
    plan: TenantPlan = Field(default="standard", description="订阅计划")
    quota_kb_count: int = Field(default=10, ge=-1, description="知识库数量限制，-1 表示无限制")
    quota_doc_count: int = Field(default=1000, ge=-1, description="文档数量限制，-1 表示无限制")
    quota_storage_mb: int = Field(default=1024, ge=-1, description="存储限制（MB），-1 表示无限制")


class TenantUpdate(BaseModel):
    """更新租户请求"""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan: TenantPlan | None = None
    quota_kb_count: int | None = Field(default=None, ge=-1)
    quota_doc_count: int | None = Field(default=None, ge=-1)
    quota_storage_mb: int | None = Field(default=None, ge=-1)
    isolation_strategy: IsolationStrategy | None = Field(default=None, description="存储隔离策略: partition/collection/auto")


class TenantResponse(BaseModel):
    """租户信息响应"""
    id: str
    name: str
    plan: str
    status: TenantStatus
    isolation_strategy: str = Field(default="auto", description="存储隔离策略")
    quota_kb_count: int
    quota_doc_count: int
    quota_storage_mb: int
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None
    disabled_reason: str | None = None
    
    # 统计信息（可选，由服务层填充）
    kb_count: int | None = None
    doc_count: int | None = None
    
    class Config:
        from_attributes = True


class TenantCreateResponse(TenantResponse):
    """创建租户响应（含初始 API Key）"""
    initial_api_key: str = Field(..., description="初始管理员 API Key，仅此时显示一次")


class TenantDisableRequest(BaseModel):
    """禁用租户请求"""
    reason: str | None = Field(default=None, max_length=500, description="禁用原因")


class TenantListResponse(BaseModel):
    """租户列表响应"""
    items: list[TenantResponse]
    total: int
    skip: int
    limit: int
