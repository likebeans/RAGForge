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
from app.services.rag import generate_rag_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag"])


@router.post("/v1/rag", response_model=RAGResponse)
async def rag_generate(
    payload: RAGRequest,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
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
    
    # 构建内部参数对象
    params = RAGParams(
        query=payload.query,
        kb_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        retriever_override=payload.retriever_override,
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
        )
        
        logger.info(
            f"RAG 生成完成: tenant={tenant.id}, query_len={len(payload.query)}, "
            f"sources={response.retrieval_count}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"RAG 生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RAG_FAILED", "detail": f"RAG 生成失败: {str(e)}"},
        )
