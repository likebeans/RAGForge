"""
RAG 生成接口

提供检索增强生成（Retrieval-Augmented Generation）API。
结合知识库检索和 LLM 生成，回答用户问题。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant
from app.auth.api_key import APIKeyContext
from app.schemas.internal import RAGParams
from app.schemas.rag import RAGRequest, RAGResponse
from app.services.query import get_tenant_kbs
from app.services.rag import generate_rag_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag"])


@router.post("/v1/rag", response_model=RAGResponse)
async def rag_generate(
    payload: RAGRequest,
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    RAG 生成接口
    
    根据用户问题从知识库检索相关内容，并使用 LLM 生成回答。
    
    流程：
    1. 从指定知识库检索相关文档片段
    2. 将检索结果作为上下文构建 prompt
    3. 调用 LLM 生成回答
    4. 返回回答和引用来源
    
    示例请求：
    ```json
    {
        "query": "什么是机器学习？",
        "knowledge_base_ids": ["kb-xxx"],
        "top_k": 5
    }
    ```
    
    示例响应：
    ```json
    {
        "answer": "机器学习是人工智能的一个分支...",
        "sources": [...],
        "model": {...}
    }
    ```
    """
    # 流式输出暂不支持
    if payload.stream:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "NOT_IMPLEMENTED", "detail": "流式输出暂不支持"},
        )
    
    # 验证知识库存在性
    kbs = await get_tenant_kbs(db, tenant_id=tenant.id, kb_ids=payload.knowledge_base_ids)
    if len(kbs) != len(set(payload.knowledge_base_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "部分知识库不存在"},
        )
    
    # 检查 API Key 的 KB 白名单 (scope_kb_ids)
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
    
    # 从 API Key 构建用户上下文（用于 ACL 权限过滤）
    user_context = api_key_ctx.get_user_context()
    
    # 构建内部参数对象
    params = RAGParams(
        query=payload.query,
        kb_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        retriever_override=payload.retriever_override,
        llm_override=payload.llm_override,
        system_prompt=payload.system_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        include_sources=payload.include_sources,
    )
    
    try:
        response = await generate_rag_response(
            session=db,
            tenant_id=tenant.id,
            params=params,
            user_context=user_context,  # 传入用户上下文用于 ACL 过滤
        )
        
        logger.info(
            f"RAG 生成完成: tenant={tenant.id}, query_len={len(payload.query)}, "
            f"sources={response.retrieval_count}"
        )
        
        return response
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NO_PERMISSION", "detail": str(e)},
        )
    except Exception as e:
        logger.error(f"RAG 生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RAG_FAILED", "detail": f"RAG 生成失败: {str(e)}"},
        )
