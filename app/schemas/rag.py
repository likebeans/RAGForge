"""
RAG 生成相关的请求/响应模型

提供检索增强生成（RAG）接口的数据模型定义。
"""

from pydantic import BaseModel, Field

from app.schemas.config import RetrieverConfig
from app.schemas.query import ChunkHit, ModelInfo


class RAGRequest(BaseModel):
    """
    RAG 生成请求
    
    示例:
    ```json
    {
        "query": "什么是机器学习",
        "knowledge_base_ids": ["kb-id-1"],
        "top_k": 5,
        "system_prompt": "你是一个专业的技术助手",
        "temperature": 0.7
    }
    ```
    """
    query: str = Field(..., min_length=1, description="用户问题")
    knowledge_base_ids: list[str] = Field(..., min_length=1, description="要搜索的知识库 ID 列表")
    top_k: int = Field(default=5, ge=1, le=20, description="检索结果数量")
    
    # 检索参数
    retriever_override: RetrieverConfig | None = Field(
        default=None,
        description="可选：临时覆盖知识库配置的检索器",
    )
    score_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="可选：过滤低于阈值的检索结果"
    )
    
    # LLM 生成参数
    system_prompt: str | None = Field(
        default=None,
        description="可选：自定义系统提示词（覆盖默认 RAG 提示词）"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0,
        description="可选：LLM 温度参数（0-2，越低越确定性）"
    )
    max_tokens: int | None = Field(
        default=None, ge=1, le=8192,
        description="可选：LLM 最大生成 token 数"
    )
    
    # 控制选项
    include_sources: bool = Field(
        default=True,
        description="是否在响应中包含检索来源"
    )
    stream: bool = Field(
        default=False,
        description="是否启用流式输出（暂不支持）"
    )


class RAGSource(BaseModel):
    """RAG 引用来源"""
    chunk_id: str = Field(description="片段 ID")
    text: str = Field(description="片段文本")
    score: float = Field(description="相关性分数")
    knowledge_base_id: str = Field(description="所属知识库 ID")
    document_id: str | None = Field(default=None, description="所属文档 ID")
    metadata: dict = Field(default_factory=dict, description="元数据")


class RAGModelInfo(BaseModel):
    """RAG 使用的模型信息"""
    # Embedding
    embedding_provider: str = Field(description="Embedding 提供商")
    embedding_model: str = Field(description="Embedding 模型")
    # LLM
    llm_provider: str = Field(description="LLM 提供商")
    llm_model: str = Field(description="LLM 模型")
    # Retriever
    retriever: str = Field(description="检索器名称")
    # Rerank（可选）
    rerank_provider: str | None = Field(default=None, description="Rerank 提供商")
    rerank_model: str | None = Field(default=None, description="Rerank 模型")


class RAGResponse(BaseModel):
    """
    RAG 生成响应
    
    示例:
    ```json
    {
        "answer": "机器学习是人工智能的一个分支...",
        "sources": [
            {"chunk_id": "xxx", "text": "相关文档片段...", "score": 0.95, ...}
        ],
        "model": {
            "llm_provider": "ollama",
            "llm_model": "qwen3:14b",
            ...
        }
    }
    ```
    """
    answer: str = Field(description="LLM 生成的回答")
    sources: list[RAGSource] = Field(
        default_factory=list,
        description="检索到的相关文档片段"
    )
    model: RAGModelInfo = Field(description="使用的模型信息")
    
    # 调试信息（可选）
    retrieval_count: int = Field(default=0, description="实际检索到的片段数")
    generation_tokens: int | None = Field(default=None, description="生成的 token 数（如可获取）")
