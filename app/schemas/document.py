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


# ============================================================
# 增强预览 API Schema
# ============================================================

class ChunkerConfigInput(BaseModel):
    """切分器配置输入"""
    name: str = Field(default="recursive", description="切分器名称")
    params: dict | None = Field(default=None, description="切分器参数")


class EnricherConfigInput(BaseModel):
    """增强器配置输入"""
    name: str = Field(default="chunk_enricher", description="增强器名称: chunk_enricher/document_summarizer")
    params: dict | None = Field(default=None, description="增强器参数")


class PreviewSummaryRequest(BaseModel):
    """预览文档摘要请求"""
    content: str = Field(..., min_length=1, description="文档内容")
    title: str | None = Field(default=None, description="文档标题（可选）")
    max_tokens: int = Field(default=300, ge=50, le=1000, description="摘要最大 token 数")


class PreviewSummaryResponse(BaseModel):
    """预览文档摘要响应"""
    summary: str = Field(..., description="生成的摘要")
    content_length: int = Field(..., description="原文长度（字符）")
    summary_length: int = Field(..., description="摘要长度（字符）")


class PreviewChunkEnrichmentRequest(BaseModel):
    """预览 Chunk 增强请求"""
    chunks: list[str] = Field(..., min_length=1, max_length=5, description="待增强的 chunk 文本列表（最多 5 个）")
    doc_title: str | None = Field(default=None, description="文档标题")
    doc_summary: str | None = Field(default=None, description="文档摘要（可选，用于增强上下文）")
    max_tokens: int = Field(default=512, ge=100, le=1000, description="增强文本最大 token 数")


class EnrichedChunkResult(BaseModel):
    """增强后的 Chunk 结果"""
    original_text: str = Field(..., description="原始文本")
    enriched_text: str = Field(..., description="增强后的文本")
    status: str = Field(..., description="增强状态: completed/failed/skipped")


class PreviewChunkEnrichmentResponse(BaseModel):
    """预览 Chunk 增强响应"""
    results: list[EnrichedChunkResult]
    total: int
    succeeded: int
    failed: int


# ============================================================
# 增强批量入库 API Schema（支持配置覆盖）
# ============================================================

class AdvancedBatchIngestItem(BaseModel):
    """高级批量上传中的单个文档（支持配置覆盖）"""
    title: str = Field(..., max_length=255, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    metadata: dict | None = Field(default=None, description="扩展元数据")
    source: str | None = Field(default=None, max_length=50, description="来源类型")


class AdvancedBatchIngestRequest(BaseModel):
    """高级批量上传请求（支持自定义配置）"""
    documents: list[AdvancedBatchIngestItem] = Field(
        ..., min_length=1, max_length=50,
        description="文档列表（最多 50 个）"
    )
    # 配置覆盖
    chunker: ChunkerConfigInput | None = Field(
        default=None,
        description="切分器配置（覆盖知识库默认配置）"
    )
    generate_summary: bool = Field(
        default=False,
        description="是否生成文档摘要"
    )
    enrich_chunks: bool = Field(
        default=False,
        description="是否对 chunks 进行 LLM 增强"
    )
    # Embedding 配置
    embedding_provider: str | None = Field(
        default=None,
        description="Embedding 提供商（覆盖知识库默认配置）"
    )
    embedding_model: str | None = Field(
        default=None,
        description="Embedding 模型（覆盖知识库默认配置）"
    )
