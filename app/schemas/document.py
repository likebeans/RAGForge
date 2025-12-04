"""文档相关的请求/响应模型"""

from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, model_validator


# 敏感度级别
SensitivityLevel = Literal["public", "internal", "restricted"]


class DocumentIngestRequest(BaseModel):
    """上传文档请求"""
    title: str = Field(..., max_length=255, description="文档标题")
    content: str | None = Field(default=None, min_length=1, description="文档内容（与 source_url 至少提供一个）")
    source_url: str | None = Field(default=None, description="可选：从 URL 拉取文本内容")
    metadata: dict | None = Field(default=None, description="扩展元数据")
    source: str | None = Field(default=None, max_length=50, description="来源类型: pdf/docx/url")
    # ACL 相关字段
    sensitivity_level: SensitivityLevel = Field(default="internal", description="敏感度级别: public/internal/restricted")
    acl_users: list[str] | None = Field(default=None, description="ACL 白名单用户列表")
    acl_roles: list[str] | None = Field(default=None, description="ACL 白名单角色列表")
    acl_groups: list[str] | None = Field(default=None, description="ACL 白名单用户组列表")

    @model_validator(mode="after")
    def ensure_content_or_url(self):
        if not self.content and not self.source_url:
            raise ValueError("content 或 source_url 必须提供其一")
        return self


class DocumentIngestResponse(BaseModel):
    """上传文档响应"""
    document_id: str  # 创建的文档 ID
    chunk_count: int  # 切分的片段数量


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    title: str
    knowledge_base_id: str
    metadata: dict | None = None
    source: str | None = None
    chunk_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: list[DocumentResponse]
    total: int
    page: int | None = None
    page_size: int | None = None
    pages: int | None = None


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应"""
    summary: str | None = None
    summary_status: str | None = None


class ChunkResponse(BaseModel):
    """Chunk 响应"""
    id: str
    document_id: str
    index: int
    text: str
    indexing_status: str
    metadata: dict | None = None

    class Config:
        from_attributes = True


class ChunkListResponse(BaseModel):
    """Chunk 列表响应"""
    items: list[ChunkResponse]
    total: int


class BatchIngestItem(BaseModel):
    """批量上传中的单个文档"""
    title: str = Field(..., max_length=255, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    metadata: dict | None = Field(default=None, description="扩展元数据")
    source: str | None = Field(default=None, max_length=50, description="来源类型")


class BatchIngestRequest(BaseModel):
    """批量上传文档请求"""
    documents: list[BatchIngestItem] = Field(..., min_length=1, max_length=50, description="文档列表（最多 50 个）")


class BatchIngestResult(BaseModel):
    """单个文档的上传结果"""
    title: str
    document_id: str | None = None
    chunk_count: int = 0
    success: bool
    error: str | None = None


class BatchIngestResponse(BaseModel):
    """批量上传响应"""
    results: list[BatchIngestResult]
    total: int
    succeeded: int
    failed: int
