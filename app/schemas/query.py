"""检索相关的请求/响应模型"""

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """模型配置信息"""
    embedding_provider: str = Field(description="Embedding 提供商")
    embedding_model: str = Field(description="Embedding 模型名称")
    llm_provider: str | None = Field(default=None, description="LLM 提供商（如使用）")
    llm_model: str | None = Field(default=None, description="LLM 模型名称（如使用）")
    rerank_provider: str | None = Field(default=None, description="Rerank 提供商（如使用）")
    rerank_model: str | None = Field(default=None, description="Rerank 模型名称（如使用）")
    retriever: str = Field(description="检索器名称")


class RetrieveRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., min_length=1, description="查询语句")
    knowledge_base_ids: list[str] = Field(..., min_length=1, description="要搜索的知识库 ID 列表")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="可选：过滤低于阈值的结果")
    metadata_filter: dict | None = Field(default=None, description="可选：按元数据精确匹配过滤结果")


class ChunkHit(BaseModel):
    """检索命中的片段"""
    chunk_id: str           # 片段 ID
    text: str               # 片段文本
    score: float            # 相似度分数 (0-1)
    metadata: dict          # 元数据
    knowledge_base_id: str  # 所属知识库
    document_id: str | None = None  # 所属文档
    # Context Window 扩展字段
    context_text: str | None = None  # 包含前后上下文的完整文本
    context_before: list[dict] | None = None  # 前置上下文 chunks
    context_after: list[dict] | None = None   # 后置上下文 chunks
    # HyDE 相关可选字段
    hyde_queries: list[str] | None = None
    hyde_queries_count: int | None = None


class RetrieveResponse(BaseModel):
    """检索响应"""
    results: list[ChunkHit]  # 检索结果列表，按相似度降序
    model: ModelInfo | None = None  # 使用的模型信息
