"""
OpenAI 兼容 API 路由

提供与 OpenAI API 兼容的接口，使得本服务可以作为 OpenAI 的替代品使用
"""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_api_key_context, get_db_session, get_tenant
from app.auth.api_key import APIKeyContext
from app.config import get_settings
from app.infra.embeddings import get_embeddings
from app.infra.logging import get_logger
from app.models import Tenant
from app.schemas.internal import RAGParams, RetrieveParams
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingUsage,
)
from app.services.query import get_tenant_kbs
from app.services.rag import generate_rag_response

logger = get_logger(__name__)
router = APIRouter(tags=["OpenAI Compatible"])


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    payload: ChatCompletionRequest,
    tenant: Tenant = Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_api_key_context),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Chat Completions API (OpenAI 兼容)
    
    支持两种模式：
    1. 纯 LLM 模式：不指定 knowledge_base_ids，直接调用 LLM
    2. RAG 模式：指定 knowledge_base_ids，自动检索知识库后生成回答
    
    **使用示例**：
    ```python
    from openai import OpenAI
    
    client = OpenAI(
        api_key="kb_sk_xxx",
        base_url="http://localhost:8020/v1"
    )
    
    # RAG 模式
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "什么是RAG？"}],
        extra_body={"knowledge_base_ids": ["kb_id_1"]}
    )
    ```
    """
    request_id = str(uuid.uuid4())
    created_at = int(time.time())
    
    # 提取用户查询（最后一条 user 消息）
    user_messages = [msg for msg in payload.messages if msg.role == "user"]
    if not user_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "detail": "至少需要一条 user 消息"},
        )
    
    query = user_messages[-1].content
    
    # 提取 system prompt（如果有）
    system_messages = [msg for msg in payload.messages if msg.role == "system"]
    system_prompt = system_messages[0].content if system_messages else None
    
    # 检查是否启用 RAG 模式
    if not payload.knowledge_base_ids:
        # 纯 LLM 模式：直接调用 LLM（暂不实现，返回提示）
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "NOT_IMPLEMENTED",
                "detail": "纯 LLM 模式暂未实现，请指定 knowledge_base_ids 使用 RAG 模式",
            },
        )
    
    # RAG 模式：检索知识库 + LLM 生成
    logger.info(
        "OpenAI Chat Completions (RAG 模式)",
        extra={
            "request_id": request_id,
            "tenant_id": tenant.id,
            "kb_ids": payload.knowledge_base_ids,
            "query": query[:100],
        },
    )
    
    # 验证知识库
    kbs = await get_tenant_kbs(db, tenant_id=tenant.id, kb_ids=payload.knowledge_base_ids)
    if len(kbs) != len(set(payload.knowledge_base_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "部分知识库不存在"},
        )
    
    # 检查 API Key 的 KB 白名单
    scope_kb_ids = api_key_ctx.api_key.scope_kb_ids
    if scope_kb_ids:
        requested_kb_ids = set(payload.knowledge_base_ids)
        allowed_kb_ids = set(scope_kb_ids)
        unauthorized_kbs = requested_kb_ids - allowed_kb_ids
        if unauthorized_kbs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "KB_NOT_IN_SCOPE",
                    "detail": f"API Key 无权访问以下知识库: {list(unauthorized_kbs)}",
                },
            )
    
    # 构建 RAG 参数
    rag_params = RAGParams(
        query=query,
        kb_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        retriever_override=payload.retriever_override,
        system_prompt=system_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        top_p=payload.top_p,
    )
    
    # 调用 RAG 服务
    try:
        rag_result = await generate_rag_response(
            session=db,
            tenant_id=tenant.id,
            params=rag_params,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG 生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RAG_GENERATION_FAILED", "detail": str(e)},
        )
    
    # 构建 OpenAI 兼容响应
    assistant_message = ChatMessage(role="assistant", content=rag_result.answer)
    choice = ChatCompletionChoice(
        index=0,
        message=assistant_message,
        finish_reason="stop",
    )
    
    # Token 使用统计（估算）
    prompt_tokens = len(query) // 4  # 粗略估算
    completion_tokens = len(rag_result.answer) // 4
    usage = ChatCompletionUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    
    # 转换 sources 格式
    sources: list[dict[str, Any]] = []
    for src in rag_result.sources:
        sources.append({
            "chunk_id": src.chunk_id,
            "text": src.text,
            "score": src.score,
            "knowledge_base_id": src.knowledge_base_id,
            "metadata": src.metadata,
        })
    
    response = ChatCompletionResponse(
        id=f"chatcmpl-{request_id}",
        created=created_at,
        model=payload.model,
        choices=[choice],
        usage=usage,
        sources=sources,  # 扩展字段：检索来源
    )
    
    return response


@router.post("/v1/embeddings", response_model=EmbeddingResponse)
async def embeddings(
    payload: EmbeddingRequest,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_api_key_context),
):
    """
    Embeddings API (OpenAI 兼容)
    
    将文本转换为向量表示
    
    **使用示例**：
    ```python
    from openai import OpenAI
    
    client = OpenAI(
        api_key="kb_sk_xxx",
        base_url="http://localhost:8020/v1"
    )
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input="Hello, world!"
    )
    print(response.data[0].embedding)
    ```
    """
    logger.info(
        "OpenAI Embeddings",
        extra={
            "tenant_id": tenant.id,
            "model": payload.model,
            "input_type": type(payload.input).__name__,
        },
    )
    
    # 统一处理输入（单个字符串或列表）
    texts = [payload.input] if isinstance(payload.input, str) else payload.input
    
    if not texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "detail": "input 不能为空"},
        )
    
    # 调用 Embedding 服务
    try:
        embeddings_list = await get_embeddings(texts)
    except Exception as e:
        logger.error(f"Embedding 生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EMBEDDING_FAILED", "detail": str(e)},
        )
    
    # 构建响应
    data = [
        EmbeddingData(
            index=i,
            embedding=emb,
        )
        for i, emb in enumerate(embeddings_list)
    ]
    
    # Token 使用统计（估算）
    total_chars = sum(len(text) for text in texts)
    prompt_tokens = total_chars // 4
    
    usage = EmbeddingUsage(
        prompt_tokens=prompt_tokens,
        total_tokens=prompt_tokens,
    )
    
    settings = get_settings()
    response = EmbeddingResponse(
        data=data,
        model=settings.embedding_model,
        usage=usage,
    )
    
    return response
