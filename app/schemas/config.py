"""算法配置相关的 Pydantic 模型

定义 Chunker、Retriever、Ingestion、Query 等配置的严格类型约束。
"""

from typing import Literal

from pydantic import BaseModel, Field


# ============ Chunker 配置 ============

ChunkerName = Literal[
    "simple",
    "sliding_window",
    "recursive",
    "markdown",
    "markdown_section",
    "code",
    "parent_child",
    "llama_sentence",
    "llama_token",
]


class ChunkerConfig(BaseModel):
    """切分器配置"""
    name: ChunkerName = Field(default="recursive", description="切分器名称")
    params: dict | None = Field(
        default=None,
        description="切分器参数，如 chunk_size, chunk_overlap 等",
        json_schema_extra={
            "examples": [
                {"chunk_size": 512, "chunk_overlap": 100},
                {"window": 256, "overlap": 50},
            ]
        },
    )


# ============ Retriever 配置 ============

RetrieverName = Literal[
    "dense",
    "bm25",
    "hybrid",
    "fusion",
    "hyde",
    "multi_query",
    "self_query",
    "parent_document",
    "ensemble",
    "llama_dense",
    "llama_bm25",
    "llama_hybrid",
]


class RetrieverConfig(BaseModel):
    """检索器配置"""
    name: RetrieverName = Field(default="dense", description="检索器名称")
    params: dict | None = Field(
        default=None,
        description="检索器参数",
        json_schema_extra={
            "examples": [
                {"base_retriever": "dense"},
                {"retrievers": ["dense", "bm25"], "weights": [0.6, 0.4]},
                {"num_queries": 3},
            ]
        },
    )


# ============ Ingestion 配置 ============

class IngestionConfig(BaseModel):
    """文档摄取配置"""
    chunker: ChunkerConfig | None = Field(
        default=None,
        description="切分器配置，默认使用 recursive chunker",
    )
    generate_summary: bool = Field(
        default=True,
        description="是否生成文档摘要",
    )
    enrich_chunks: bool = Field(
        default=False,
        description="是否增强 chunks（添加上下文信息）",
    )


# ============ Query 配置 ============

class QueryConfig(BaseModel):
    """检索查询配置"""
    retriever: RetrieverConfig | None = Field(
        default=None,
        description="检索器配置，默认使用 dense retriever",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="默认返回结果数量",
    )
    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="默认分数阈值",
    )


# ============ 知识库完整配置 ============

class KBConfig(BaseModel):
    """知识库配置

    示例:
    ```json
    {
        "ingestion": {
            "chunker": {"name": "markdown", "params": {"chunk_size": 512}}
        },
        "query": {
            "retriever": {"name": "hybrid"},
            "top_k": 10
        }
    }
    ```
    """
    ingestion: IngestionConfig | None = Field(
        default=None,
        description="文档摄取配置",
    )
    query: QueryConfig | None = Field(
        default=None,
        description="检索查询配置",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ingestion": {
                    "chunker": {"name": "markdown", "params": {"chunk_size": 512, "chunk_overlap": 100}},
                    "generate_summary": True,
                },
                "query": {
                    "retriever": {"name": "hyde", "params": {"base_retriever": "dense"}},
                    "top_k": 10,
                },
            }
        }
