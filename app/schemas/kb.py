"""知识库相关的请求/响应模型"""

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., max_length=255, description="知识库名称")
    description: str | None = Field(default=None, max_length=500, description="描述信息")
    config: dict | None = Field(default=None, description="配置信息（分块策略等）")


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    name: str
    description: str | None
    config: dict | None = None

    class Config:
        from_attributes = True  # 允许从 ORM 对象构造


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: str | None = Field(default=None, max_length=255, description="知识库名称")
    description: str | None = Field(default=None, max_length=500, description="描述信息")
    config: dict | None = Field(default=None, description="配置信息（分块/检索策略等）")


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: list[KnowledgeBaseResponse]
    total: int
    page: int | None = None
    page_size: int | None = None
    pages: int | None = None
