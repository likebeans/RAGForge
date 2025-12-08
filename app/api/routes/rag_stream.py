"""
流式 RAG 生成路由

提供 SSE (Server-Sent Events) 流式输出，用于前端实时展示生成内容。

事件类型：
- sources: 检索到的引用来源
- content: LLM 生成的文本片段
- done: 生成完成
- error: 错误信息
"""

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import APIKeyContext, get_current_api_key, get_db_session, get_tenant
from app.infra.llm import chat_completion_stream
from app.models import KnowledgeBase
from app.models.tenant import Tenant
from app.schemas.conversation import StreamRAGRequest
from app.schemas.internal import RetrieveParams
from app.services.query import retrieve_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["rag-stream"])


async def _sse_generator(
    query: str,
    kb_ids: list[str],
    retriever: str,
    top_k: int,
    tenant_id: str,
    kbs: list[KnowledgeBase],
    session: AsyncSession,
    api_key_ctx: APIKeyContext,
) -> AsyncIterator[str]:
    """
    SSE 事件生成器
    
    流程：
    1. 执行检索，返回 sources 事件
    2. 构建 prompt，流式调用 LLM
    3. 逐个 token 返回 content 事件
    4. 完成后返回 done 事件
    """
    try:
        # Step 1: 检索相关文档
        retrieve_params = RetrieveParams(
            query=query,
            top_k=top_k,
            retriever_override={"name": retriever} if retriever != "dense" else None,
        )
        
        # 构建 user_context 用于 ACL 过滤
        user_context = api_key_ctx.get_user_context()
        
        chunks, retriever_name, acl_blocked = await retrieve_chunks(
            tenant_id=tenant_id,
            kbs=kbs,
            params=retrieve_params,
            session=session,
            user_context=user_context,
        )
        
        if acl_blocked:
            yield f"event: error\ndata: {json.dumps({'error': 'ACL 权限过滤，无可用检索结果'})}\n\n"
            return
        
        # 构建 sources 数据
        sources = []
        for chunk in chunks:
            metadata = chunk.metadata or {}
            sources.append({
                "text": (chunk.text or "")[:200] + "...",  # 截断显示
                "score": chunk.score or 0,
                "chunk_id": chunk.chunk_id,
                "document_title": metadata.get("document_title"),
                "knowledge_base_id": chunk.knowledge_base_id,
            })
        
        # 发送 sources 事件
        yield f"event: sources\ndata: {json.dumps(sources, ensure_ascii=False)}\n\n"
        
        if not chunks:
            yield f"event: content\ndata: 未找到相关文档，无法回答您的问题。\n\n"
            yield "event: done\ndata: \n\n"
            return
        
        # Step 2: 构建 RAG prompt
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.text or ""
            metadata = chunk.metadata or {}
            doc_title = metadata.get("document_title", "未知文档")
            context_parts.append(f"[{i}] {doc_title}:\n{text}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        system_prompt = """你是一个专业的知识库问答助手。请根据提供的参考资料回答用户问题。

要求：
1. 只使用参考资料中的信息回答，不要编造内容
2. 如果参考资料不足以回答问题，请明确说明
3. 回答要准确、简洁、有条理
4. 可以引用具体的文档来源"""

        user_prompt = f"""参考资料：
{context}

用户问题：{query}

请根据以上参考资料回答用户问题。"""

        # Step 3: 流式调用 LLM
        async for chunk in chat_completion_stream(
            prompt=user_prompt,
            system_prompt=system_prompt,
        ):
            # 转义特殊字符
            escaped = chunk.replace("\n", "\\n").replace("\r", "\\r")
            yield f"event: content\ndata: {escaped}\n\n"
        
        # Step 4: 发送完成事件
        yield "event: done\ndata: \n\n"
        
    except Exception as e:
        logger.exception(f"SSE 流式生成失败: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def rag_stream(
    payload: StreamRAGRequest,
    tenant: Tenant = Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    流式 RAG 生成
    
    使用 SSE (Server-Sent Events) 返回流式响应：
    
    事件格式：
    ```
    event: sources
    data: [{"text": "...", "score": 0.89, ...}, ...]
    
    event: content
    data: 这是
    
    event: content
    data: 生成的
    
    event: content
    data: 内容
    
    event: done
    data: 
    ```
    
    前端示例：
    ```javascript
    const eventSource = new EventSource('/v1/rag/stream');
    eventSource.addEventListener('sources', (e) => console.log(JSON.parse(e.data)));
    eventSource.addEventListener('content', (e) => console.log(e.data));
    eventSource.addEventListener('done', () => eventSource.close());
    ```
    """
    # 验证知识库存在
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id.in_(payload.knowledge_base_ids),
        KnowledgeBase.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    kbs = list(result.scalars().all())
    
    if len(kbs) != len(set(payload.knowledge_base_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "部分知识库不存在"},
        )
    
    # 检查 API Key 的 scope_kb_ids 权限
    scope_kb_ids = api_key_ctx.api_key.scope_kb_ids
    if scope_kb_ids:
        unauthorized = set(payload.knowledge_base_ids) - set(scope_kb_ids)
        if unauthorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "KB_NOT_IN_SCOPE",
                    "detail": f"API Key 无权访问以下知识库: {list(unauthorized)}",
                },
            )
    
    # 返回 SSE 流式响应
    return StreamingResponse(
        _sse_generator(
            query=payload.query,
            kb_ids=payload.knowledge_base_ids,
            retriever=payload.retriever,
            top_k=payload.top_k,
            tenant_id=tenant.id,
            kbs=kbs,
            session=db,
            api_key_ctx=api_key_ctx,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
