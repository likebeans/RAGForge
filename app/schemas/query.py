"""检索相关的请求/响应模型"""

from pydantic import BaseModel, Field

from app.schemas.config import RetrieverConfig


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
    """检索请求

    示例:
    ```json
    {
        "query": "什么是机器学习",
        "knowledge_base_ids": ["kb-id-1"],
        "top_k": 5,
        "retriever_override": {"name": "hyde", "params": {"base_retriever": "dense"}}
    }
    ```
    """
    query: str = Field(..., min_length=1, description="查询语句")
    knowledge_base_ids: list[str] = Field(..., min_length=1, description="要搜索的知识库 ID 列表")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="可选：过滤低于阈值的结果")
    metadata_filter: dict | None = Field(default=None, description="可选：按元数据精确匹配过滤结果")
    retriever_override: RetrieverConfig | None = Field(
        default=None,
        description="可选：临时覆盖知识库配置的检索器",
        json_schema_extra={
            "examples": [
                {"name": "dense"},
                {"name": "bm25"},
                {"name": "hybrid"},
                {"name": "hyde", "params": {"base_retriever": "dense"}},
                {"name": "multi_query", "params": {"num_queries": 3}},
                {"name": "ensemble", "params": {"retrievers": ["dense", "bm25"], "weights": [0.6, 0.4]}},
            ]
        },
    )
    rerank: bool = Field(
        default=False,
        description="可选：是否启用 Rerank 后处理（使用配置的 Rerank 提供商）",
    )
    rerank_top_k: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="可选：Rerank 后返回的结果数量，默认等于 top_k",
    )


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
    # multi_query 相关可选字段
    generated_queries: list[str] | None = None
    queries_count: int | None = None
    retrieval_details: list[dict] | None = None  # 每个查询的完整检索结果


class RetrieveResponse(BaseModel):
    """检索响应"""
    results: list[ChunkHit]  # 检索结果列表，按相似度降序
    model: ModelInfo | None = None  # 使用的模型信息
