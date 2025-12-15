"""Playground / Pipeline 可视化相关的请求/响应模型"""

from typing import Any
from pydantic import BaseModel, Field

from app.schemas.config import EmbeddingOverrideConfig, LLMConfig, RerankConfig, RetrieverConfig
from app.schemas.query import ChunkHit
from app.schemas.rag import RAGModelInfo


class OperatorMeta(BaseModel):
    """算子元数据"""
    kind: str = Field(description="算子类型，如 chunker/retriever")
    name: str = Field(description="算子内部名称")
    label: str = Field(description="展示名称")
    description: str | None = Field(default=None, description="简要说明")
    params_schema: dict[str, Any] | None = Field(
        default=None,
        description="可选参数示例（暂为简化版）",
    )


class OperatorListResponse(BaseModel):
    """算子列表"""
    chunkers: list[OperatorMeta] = Field(default_factory=list)
    retrievers: list[OperatorMeta] = Field(default_factory=list)
    query_transforms: list[OperatorMeta] = Field(default_factory=list)
    enrichers: list[OperatorMeta] = Field(default_factory=list)
    postprocessors: list[OperatorMeta] = Field(default_factory=list)


class PlaygroundRunRequest(BaseModel):
    """Playground 单次实验请求"""
    query: str = Field(..., min_length=1, description="用户问题")
    knowledge_base_ids: list[str] = Field(..., min_length=1, description="知识库 ID 列表")
    top_k: int = Field(default=5, ge=1, le=50, description="检索返回数量")
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="分数阈值")
    retriever: RetrieverConfig | None = Field(default=None, description="覆盖检索器配置")
    rerank: bool = Field(default=False, description="是否启用 Rerank")
    rerank_override: RerankConfig | None = Field(default=None, description="Rerank 覆盖配置")
    rerank_top_k: int | None = Field(default=None, ge=1, le=100, description="Rerank 返回数量")
    chunker: str | None = Field(default=None, description="用于预览的切分器名称")
    chunker_params: dict | None = Field(default=None, description="切分器参数")
    chunk_preview_text: str | None = Field(default=None, description="可选：输入一段文本用于切分预览")
    llm_override: LLMConfig | None = Field(default=None, description="覆盖默认 LLM 配置")
    embedding_override: EmbeddingOverrideConfig | None = Field(default=None, description="覆盖默认 Embedding 配置")


class ChunkPreview(BaseModel):
    """切分预览"""
    chunk_id: str
    text: str
    metadata: dict | None = None


class QueryTransformPreview(BaseModel):
    """查询增强/变换信息"""
    original_query: str
    generated_queries: list[str] | None = None
    hyde_prompts: list[str] | None = None


class RetrievalPreview(BaseModel):
    """检索阶段结果"""
    retriever: str
    latency_ms: float
    rerank_applied: bool | None = None
    results: list[ChunkHit]


class RagPreview(BaseModel):
    """RAG 回答阶段结果"""
    answer: str
    sources: list[ChunkHit] = Field(default_factory=list)
    model: RAGModelInfo
    latency_ms: float


class PlaygroundRunResponse(BaseModel):
    """Playground 单次实验响应"""
    query: str
    knowledge_base_ids: list[str]
    chunk_preview: list[ChunkPreview] | None = None
    query_transform: QueryTransformPreview | None = None
    retrieval: RetrievalPreview
    rag: RagPreview
    metrics: dict[str, float] = Field(default_factory=dict, description="耗时等指标")
