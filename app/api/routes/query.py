"""
检索接口 (OpenAI 兼容扩展)

提供知识库检索能力，返回与查询最相关的文档片段。
这是 RAG 的核心接口，Agent 可以调用此接口获取知识。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant
from app.auth.api_key import APIKeyContext
from app.config import get_settings
from app.exceptions import KBConfigError
from app.schemas import RetrieveRequest, RetrieveResponse
from app.schemas.internal import RetrieveParams
from app.schemas.query import ModelInfo
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
    
    # 构建检索参数对象
    params = RetrieveParams(
        query=payload.query,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        metadata_filter=payload.metadata_filter,
        retriever_override=payload.retriever_override,
        rerank=payload.rerank,
        rerank_top_k=payload.rerank_top_k,
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

    # 构建模型信息
    settings = get_settings()
    embed_config = settings.get_embedding_config()
    llm_config = settings.get_llm_config()
    rerank_config = settings.get_rerank_config()
    
    # 判断是否使用了 LLM（hyde、multi_query、self_query 等检索器需要 LLM）
    llm_retrievers = {"hyde", "multi_query", "self_query"}
    uses_llm = retriever_name in llm_retrievers
    
    # 判断是否使用 Rerank（fusion 检索器内置 rerank 或用户显式启用 rerank 参数）
    rerank_retrievers = {"fusion"}
    uses_rerank = (
        (retriever_name in rerank_retrievers or payload.rerank) 
        and rerank_config.get("provider") != "none"
    )
    
    model_info = ModelInfo(
        embedding_provider=embed_config["provider"],
        embedding_model=embed_config["model"],
        llm_provider=llm_config["provider"] if uses_llm else None,
        llm_model=llm_config["model"] if uses_llm else None,
        rerank_provider=rerank_config.get("provider") if uses_rerank else None,
        rerank_model=rerank_config.get("model") if uses_rerank else None,
        retriever=retriever_name,
    )

    return RetrieveResponse(results=results, model=model_info)
