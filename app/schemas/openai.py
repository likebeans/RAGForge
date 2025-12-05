"""
OpenAI 兼容 API Schema

提供与 OpenAI API 兼容的请求/响应模型
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# Chat Completions
# ============================================================================


class ChatMessage(BaseModel):
    """聊天消息"""

    role: Literal["system", "user", "assistant"] = Field(..., description="角色")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    """Chat Completion 请求 (OpenAI 兼容)"""

    model: str = Field(..., description="模型名称")
    messages: list[ChatMessage] = Field(..., description="消息列表")
    temperature: float | None = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int | None = Field(default=None, ge=1, description="最大生成 token 数")
    top_p: float | None = Field(default=1.0, ge=0, le=1, description="Top-p 采样")
    stream: bool = Field(default=False, description="是否流式返回")

    # 扩展字段：知识库检索
    knowledge_base_ids: list[str] | None = Field(default=None, description="知识库 ID 列表（启用 RAG）")
    top_k: int = Field(default=5, ge=1, le=50, description="检索 top-k 文档数")
    score_threshold: float | None = Field(default=None, ge=0, le=1, description="相似度阈值")
    retriever_override: dict[str, Any] | None = Field(default=None, description="检索器覆盖配置")


class ChatCompletionChoice(BaseModel):
    """Chat Completion 选项"""

    index: int = Field(..., description="选项索引")
    message: ChatMessage = Field(..., description="生成的消息")
    finish_reason: Literal["stop", "length", "content_filter"] = Field(..., description="结束原因")


class ChatCompletionUsage(BaseModel):
    """Token 使用统计"""

    prompt_tokens: int = Field(..., description="输入 token 数")
    completion_tokens: int = Field(..., description="生成 token 数")
    total_tokens: int = Field(..., description="总 token 数")


class ChatCompletionResponse(BaseModel):
    """Chat Completion 响应 (OpenAI 兼容)"""

    id: str = Field(..., description="请求 ID")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: list[ChatCompletionChoice] = Field(..., description="生成结果列表")
    usage: ChatCompletionUsage | None = Field(default=None, description="Token 使用统计")

    # 扩展字段：检索来源
    sources: list[dict[str, Any]] | None = Field(default=None, description="检索来源（RAG 模式）")


# ============================================================================
# Embeddings
# ============================================================================


class EmbeddingRequest(BaseModel):
    """Embedding 请求 (OpenAI 兼容)"""

    model: str = Field(..., description="模型名称")
    input: str | list[str] = Field(..., description="输入文本或文本列表")
    encoding_format: Literal["float", "base64"] = Field(default="float", description="编码格式")


class EmbeddingData(BaseModel):
    """单个 Embedding 数据"""

    object: Literal["embedding"] = "embedding"
    index: int = Field(..., description="索引")
    embedding: list[float] = Field(..., description="向量")


class EmbeddingUsage(BaseModel):
    """Embedding Token 使用统计"""

    prompt_tokens: int = Field(..., description="输入 token 数")
    total_tokens: int = Field(..., description="总 token 数")


class EmbeddingResponse(BaseModel):
    """Embedding 响应 (OpenAI 兼容)"""

    object: Literal["list"] = "list"
    data: list[EmbeddingData] = Field(..., description="Embedding 列表")
    model: str = Field(..., description="使用的模型")
    usage: EmbeddingUsage = Field(..., description="Token 使用统计")
