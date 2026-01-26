"""
检索接口 (OpenAI 兼容扩展)

提供知识库检索能力，返回与查询最相关的文档片段。
这是 RAG 的核心接口，Agent 可以调用此接口获取知识。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant

logger = logging.getLogger(__name__)
from app.auth.api_key import APIKeyContext
from app.exceptions import KBConfigError
from app.schemas import RetrieveRequest, RetrieveResponse
from app.schemas.config import EmbeddingOverrideConfig
from app.schemas.internal import RetrieveParams
from app.schemas.query import ModelInfo
from app.services.model_config import model_config_resolver
from app.services.query import get_tenant_kbs, retrieve_chunks

router = APIRouter()


@router.post("/v1/retrieve", response_model=RetrieveResponse)
async def retrieve(
    payload: RetrieveRequest,
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    检索知识库
    
    根据查询语句，从指定的知识库中检索最相关的文档片段。
    
    检索流程：
    1. 验证请求的知识库是否都属于当前租户
    2. 将查询语句向量化
    3. 在向量数据库中进行相似度搜索
    4. 返回 top_k 个最相关的片段
    """
    # 验证所有请求的知识库都属于当前租户
    kbs = await get_tenant_kbs(db, tenant_id=tenant.id, kb_ids=payload.knowledge_base_ids)
    if len(kbs) != len(set(payload.knowledge_base_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "One or more knowledge bases not found for tenant"},
        )
    
    # 检查 API Key 的 KB 白名单 (scope_kb_ids)
    scope_kb_ids = api_key_ctx.api_key.scope_kb_ids
    if scope_kb_ids:
        # 如果设置了白名单，检查请求的 KB 是否都在白名单中
        requested_kb_ids = set(payload.knowledge_base_ids)
        allowed_kb_ids = set(scope_kb_ids)
        unauthorized_kbs = requested_kb_ids - allowed_kb_ids
        if unauthorized_kbs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "KB_NOT_IN_SCOPE",
                    "detail": f"API Key 无权访问以下知识库: {list(unauthorized_kbs)}"
                },
            )
    
    # 使用 ModelConfigResolver 获取 Embedding 配置（优先使用租户/知识库配置）
    logger.info(f"[DEBUG] tenant.id={tenant.id}, tenant.model_settings={tenant.model_settings}")
    embed_config = await model_config_resolver.get_embedding_config(
        session=db, 
        kb=kbs[0] if kbs else None, 
        tenant=tenant,
    )
    logger.info(f"[DEBUG] embed_config={embed_config}")
    
    # 构建带有租户 API Key 的 provider 配置
    try:
        provider_config = model_config_resolver.build_provider_config(
            embed_config, "embedding", tenant=tenant
        )
        logger.info(f"[DEBUG] provider_config={provider_config}")
        # 构建 embedding_override 传递给检索服务
        embedding_override = EmbeddingOverrideConfig(
            provider=provider_config.get("provider"),
            model=provider_config.get("model"),
            api_key=provider_config.get("api_key"),
            base_url=provider_config.get("base_url"),
        )
    except ValueError:
        # 如果没有配置 embedding 提供商，使用 None（回退到环境变量）
        embedding_override = None
    
    # 构建检索参数对象
    params = RetrieveParams(
        query=payload.query,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        metadata_filter=payload.metadata_filter,
        retriever_override=payload.retriever_override,
        rerank=payload.rerank,
        rerank_top_k=payload.rerank_top_k,
        embedding_override=embedding_override,
    )
    
    # 从 API Key 构建用户上下文（用于 ACL 权限过滤）
    user_context = api_key_ctx.get_user_context()
    
    try:
        results, retriever_name, acl_blocked = await retrieve_chunks(
            tenant_id=tenant.id,
            kbs=kbs,
            params=params,
            session=db,  # 传入 session 用于 Context Window
            user_context=user_context,  # 传入用户上下文用于 Security Trimming
            tenant=tenant,  # 传入 tenant 用于获取 model_settings 中的 API key
        )
    except KBConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "KB_CONFIG_ERROR", "detail": str(e)},
        )

    if acl_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NO_PERMISSION", "detail": "检索结果已被权限控制过滤，请检查文档敏感度或 API Key 权限"},
        )

    # 获取 LLM 和 Rerank 配置（用于构建模型信息响应）
    llm_config = await model_config_resolver.get_llm_config(session=db, tenant=tenant)
    rerank_config = await model_config_resolver.get_rerank_config(session=db, tenant=tenant)
    
    # 判断是否使用了 LLM（hyde、multi_query、self_query 等检索器需要 LLM）
    llm_retrievers = {"hyde", "multi_query", "self_query"}
    uses_llm = retriever_name in llm_retrievers
    
    # 判断是否使用 Rerank（fusion 检索器内置 rerank 或用户显式启用 rerank 参数）
    rerank_retrievers = {"fusion"}
    uses_rerank = (
        (retriever_name in rerank_retrievers or payload.rerank) 
        and rerank_config.get("rerank_provider") != "none"
    )
    
    model_info = ModelInfo(
        embedding_provider=embed_config.get("embedding_provider", ""),
        embedding_model=embed_config.get("embedding_model", ""),
        llm_provider=llm_config.get("llm_provider") if uses_llm else None,
        llm_model=llm_config.get("llm_model") if uses_llm else None,
        rerank_provider=rerank_config.get("rerank_provider") if uses_rerank else None,
        rerank_model=rerank_config.get("rerank_model") if uses_rerank else None,
        retriever=retriever_name,
    )

    return RetrieveResponse(results=results, model=model_info)
