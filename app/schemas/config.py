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
    "raptor",  # RAPTOR 多层次索引检索
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


# ============ Embedding 配置 ============

EmbeddingProvider = Literal[
    "ollama",
    "openai",
    "gemini",
    "qwen",
    "zhipu",
    "siliconflow",
    "deepseek",
    "kimi",
]


class EmbeddingConfig(BaseModel):
    """Embedding 模型配置
    
    知识库可以指定独立的 Embedding 配置，覆盖系统/租户默认值。
    注意：一旦知识库有文档，不建议更改 Embedding 配置，因为会导致向量维度不兼容。
    """
    provider: EmbeddingProvider | None = Field(
        default=None,
        description="Embedding 提供商",
    )
    model: str | None = Field(
        default=None,
        description="Embedding 模型名称",
    )
    dim: int | None = Field(
        default=None,
        ge=1,
        le=8192,
        description="向量维度（可选，用于校验）",
    )


class EmbeddingOverrideConfig(BaseModel):
    """Embedding 覆盖配置
    
    用于请求级覆盖 Embedding 配置，优先级最高。
    """
    provider: EmbeddingProvider = Field(
        ...,
        description="Embedding 提供商",
    )
    model: str = Field(
        ...,
        description="Embedding 模型名称",
    )
    api_key: str | None = Field(
        default=None,
        description="API Key（可选，未指定时使用系统配置）",
    )
    base_url: str | None = Field(
        default=None,
        description="API Base URL（可选，未指定时使用系统配置）",
    )


# ============ LLM 配置 ============

LLMProvider = Literal[
    "ollama",
    "openai",
    "gemini",
    "qwen",
    "zhipu",
    "siliconflow",
    "deepseek",
    "kimi",
]


class LLMConfig(BaseModel):
    """LLM 模型配置
    
    用于请求级覆盖 LLM 配置，优先级最高。
    """
    provider: LLMProvider = Field(
        ...,
        description="LLM 提供商",
    )
    model: str = Field(
        ...,
        description="LLM 模型名称",
    )
    api_key: str | None = Field(
        default=None,
        description="API Key（可选，未指定时使用系统配置）",
    )
    base_url: str | None = Field(
        default=None,
        description="API Base URL（可选，未指定时使用系统配置）",
    )


# ============ Rerank 配置 ============

RerankProvider = Literal[
    "ollama",
    "cohere",
    "zhipu",
    "siliconflow",
    "vllm",
]


class RerankConfig(BaseModel):
    """Rerank 模型配置
    
    用于请求级覆盖 Rerank 配置，优先级最高。
    """
    provider: RerankProvider = Field(
        ...,
        description="Rerank 提供商",
    )
    model: str = Field(
        ...,
        description="Rerank 模型名称",
    )
    api_key: str | None = Field(
        default=None,
        description="API Key（可选，未指定时使用系统配置）",
    )
    base_url: str | None = Field(
        default=None,
        description="Base URL（可选，未指定时使用系统配置）",
    )


# ============ RAPTOR 配置 ============

RaptorClusterMethod = Literal["gmm", "kmeans"]


class RaptorConfig(BaseModel):
    """RAPTOR 索引配置
    
    RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)
    通过递归聚类和摘要构建多层次索引树。
    
    示例:
    ```json
    {
        "enabled": true,
        "max_layers": 3,
        "cluster_method": "gmm",
        "min_cluster_size": 3,
        "summary_num_workers": 4
    }
    ```
    """
    enabled: bool = Field(
        default=False,
        description="是否启用 RAPTOR 索引",
    )
    max_layers: int = Field(
        default=3,
        ge=1,
        le=5,
        description="最大层数（1-5），层数越多索引越深",
    )
    cluster_method: RaptorClusterMethod = Field(
        default="gmm",
        description="聚类方法：gmm（高斯混合模型）或 kmeans",
    )
    min_cluster_size: int = Field(
        default=3,
        ge=2,
        le=20,
        description="最小聚类大小，小于此值的聚类不会生成摘要",
    )
    summary_num_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="摘要生成并发数",
    )
    summary_prompt: str | None = Field(
        default=None,
        description="自定义摘要提示词（可选）",
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
        },
        "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small"
        },
        "raptor": {
            "enabled": true,
            "max_layers": 3
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
    embedding: EmbeddingConfig | None = Field(
        default=None,
        description="Embedding 模型配置（覆盖系统/租户默认值）",
    )
    raptor: RaptorConfig | None = Field(
        default=None,
        description="RAPTOR 索引配置",
    )
    model_config = {
        "json_schema_extra": {
            "example": {
                "ingestion": {
                    "chunker": {"name": "markdown", "params": {"chunk_size": 512, "chunk_overlap": 100}},
                    "generate_summary": True,
                },
                "query": {
                    "retriever": {"name": "hyde", "params": {"base_retriever": "dense"}},
                    "top_k": 10,
                },
                "embedding": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                },
            }
        }
    }
