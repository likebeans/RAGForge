"""
对话相关的请求/响应模型

用于前端聊天历史持久化的 API 接口。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.config import LLMConfig


# ==================== 引用来源 ====================

class SourceItem(BaseModel):
    """引用来源项"""
    text: str = Field(..., description="文本片段")
    score: float = Field(..., description="相关度分数")
    document_title: str | None = Field(default=None, description="文档标题")
    chunk_id: str | None = Field(default=None, description="Chunk ID")
    knowledge_base_id: str | None = Field(default=None, description="知识库 ID")


# ==================== 消息 ====================

class MessageCreate(BaseModel):
    """创建消息请求"""
    role: Literal["user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")
    retriever: str | None = Field(default=None, description="使用的检索器")
    sources: list[SourceItem] | None = Field(default=None, description="引用来源")
    metadata: dict | None = Field(default=None, description="额外元数据")


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    role: str
    content: str
    retriever: str | None = None
    sources: list[SourceItem] | None = None
    metadata: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 对话 ====================

class ConversationCreate(BaseModel):
    """创建对话请求
    
    示例:
    ```json
    {
        "title": "关于药食同源的咨询",
        "knowledge_base_ids": ["kb-uuid-1", "kb-uuid-2"]
    }
    ```
    """
    title: str | None = Field(default=None, max_length=255, description="对话标题")
    knowledge_base_ids: list[str] | None = Field(
        default=None, 
        description="关联的知识库 ID 列表"
    )


class ConversationUpdate(BaseModel):
    """更新对话请求"""
    title: str | None = Field(default=None, max_length=255, description="对话标题")
    knowledge_base_ids: list[str] | None = Field(
        default=None, 
        description="关联的知识库 ID 列表"
    )


class ConversationResponse(BaseModel):
    """对话响应（不含消息）"""
    id: str
    title: str | None = None
    knowledge_base_ids: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int | None = None  # 消息数量（可选）

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """对话详情响应（含消息）"""
    id: str
    title: str | None = None
    knowledge_base_ids: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    items: list[ConversationResponse]
    total: int
    page: int | None = None
    page_size: int | None = None


# ==================== 流式 RAG ====================

class StreamRAGRequest(BaseModel):
    """流式 RAG 请求
    
    示例:
    ```json
    {
        "query": "药食同源物品有哪些？",
        "knowledge_base_ids": ["kb-uuid"],
        "retriever": "hybrid",
        "top_k": 5,
        "conversation_id": "conv-uuid"
    }
    ```
    """
    query: str = Field(..., min_length=1, description="用户问题")
    knowledge_base_ids: list[str] = Field(..., min_length=1, description="知识库 ID 列表")
    retriever: str = Field(default="hybrid", description="检索器名称")
    top_k: int = Field(default=5, ge=1, le=50, description="检索数量")
    conversation_id: str | None = Field(
        default=None, 
        description="对话 ID（用于上下文关联和消息保存）"
    )
    save_message: bool = Field(
        default=True, 
        description="是否保存消息到对话历史"
    )
    llm_override: LLMConfig | None = Field(
        default=None,
        description="临时覆盖默认的 LLM 配置"
    )


class StreamEvent(BaseModel):
    """SSE 事件模型"""
    event: Literal["sources", "content", "done", "error"]
    data: str
