"""
RAG 生成服务 (Retrieval-Augmented Generation)

提供检索增强生成功能：
1. 从知识库检索相关文档片段
2. 构建包含上下文的 prompt
3. 调用 LLM 生成回答
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infra.llm import chat_completion, chat_completion_with_config
from app.models import KnowledgeBase, Tenant
from app.schemas.internal import RAGParams, RetrieveParams
from app.schemas.config import LLMConfig
from app.schemas.query import ChunkHit
from app.schemas.rag import RAGModelInfo, RAGResponse, RAGSource
from app.services.acl import UserContext
from app.services.model_config import model_config_resolver
from app.services.query import get_tenant_kbs, retrieve_chunks

logger = logging.getLogger(__name__)


# 默认 RAG 系统提示词
DEFAULT_RAG_SYSTEM_PROMPT = """你是一个专业的知识库问答助手。请根据提供的参考资料回答用户的问题。

要求：
1. 只根据参考资料中的信息回答，不要编造内容
2. 如果参考资料中没有相关信息，请诚实说明
3. 回答要简洁、准确、有条理
4. 适当引用资料来源，增强可信度"""

# 上下文模板
CONTEXT_TEMPLATE = """以下是与问题相关的参考资料：

{context}

---
用户问题：{query}"""


@dataclass
class RAGResult:
    """RAG 内部结果"""
    answer: str
    sources: list[ChunkHit]
    retriever_name: str


async def generate_rag_response(
    *,
    session: AsyncSession,
    tenant_id: str,
    params: RAGParams,
    user_context: UserContext | None = None,
    tenant: "Tenant | None" = None,
) -> RAGResponse:
    """
    执行 RAG 生成
    
    流程：
    1. 获取知识库列表
    2. 检索相关文档片段（带 ACL 过滤）
    3. 构建 prompt
    4. 调用 LLM 生成回答
    5. 组装响应
    
    Args:
        session: 数据库会话
        tenant_id: 租户 ID
        params: RAG 参数对象，包含查询、检索和 LLM 相关配置
        user_context: 用户上下文（用于 ACL 权限过滤）
    
    Returns:
        RAGResponse: 包含回答和来源的响应
    """
    settings = get_settings()
    
    # 获取租户 LLM 配置（如果未提供 llm_override 则使用租户配置）
    llm_provider_config = None
    if tenant and not params.llm_override:
        try:
            llm_config = await model_config_resolver.get_llm_config(session, tenant=tenant)
            llm_provider_config = model_config_resolver.build_provider_config(
                llm_config, "llm", tenant=tenant
            )
            logger.info(f"RAG: 使用租户 LLM 配置: provider={llm_provider_config.get('provider')}, model={llm_provider_config.get('model')}")
        except Exception as e:
            logger.warning(f"RAG: 获取租户 LLM 配置失败，使用环境变量默认值: {e}")
    
    # 1. 获取知识库
    kbs = await get_tenant_kbs(session, tenant_id, params.kb_ids)
    if not kbs:
        # 无知识库时直接回答
        logger.warning(f"RAG: 未找到知识库 {params.kb_ids}")
        answer = await _generate_without_context(
            params.query,
            params.system_prompt,
            params.temperature,
            params.max_tokens,
            params.llm_override,
            llm_provider_config,
        )
        return _build_response(
            answer=answer,
            sources=[],
            retriever_name="none",
            settings=settings,
            llm_override=params.llm_override,
            embedding_override=params.embedding_override.model_dump() if params.embedding_override else None,
            rerank_override=params.rerank_override.model_dump() if params.rerank_override else None,
        )
    
    # 2. 检索相关片段
    retrieve_params = RetrieveParams(
        query=params.query,
        top_k=params.top_k,
        score_threshold=params.score_threshold,
        retriever_override=params.retriever_override,
        embedding_override=params.embedding_override,
    )
    chunks, retriever_name, acl_blocked = await retrieve_chunks(
        tenant_id=tenant_id,
        kbs=kbs,
        params=retrieve_params,
        session=session,
        user_context=user_context,  # 传入用户上下文用于 Security Trimming
        tenant=tenant,  # 传入 tenant 用于获取 model_settings 中的 API key
    )
    if acl_blocked:
        raise PermissionError("检索结果因 ACL 权限控制被过滤，请检查文档敏感度或 API Key 权限")
    
    logger.info(f"RAG: 检索到 {len(chunks)} 个相关片段，使用检索器 {retriever_name}")
    
    # 3. 构建 prompt 并生成回答
    if not chunks:
        # 无相关内容时提示
        answer = await _generate_without_context(
            params.query,
            params.system_prompt,
            params.temperature,
            params.max_tokens,
            params.llm_override,
            llm_provider_config,
        )
    else:
        answer = await _generate_with_context(
            query=params.query,
            chunks=chunks,
            system_prompt=params.system_prompt,
            temperature=params.temperature,
            max_tokens=params.max_tokens,
            llm_override=params.llm_override,
            llm_provider_config=llm_provider_config,
        )
    
    # 4. 构建响应
    sources = []
    if params.include_sources:
        sources = [
            RAGSource(
                chunk_id=c.chunk_id,
                text=c.text,
                score=c.score,
                knowledge_base_id=c.knowledge_base_id,
                document_id=c.document_id,
                metadata=c.metadata,
            )
            for c in chunks
        ]
    
    return _build_response(
        answer=answer,
        sources=sources,
        retriever_name=retriever_name,
        settings=settings,
        llm_override=params.llm_override,
        embedding_override=params.embedding_override.model_dump() if params.embedding_override else None,
        rerank_override=params.rerank_override.model_dump() if params.rerank_override else None,
        retrieval_count=len(chunks),
    )


async def _generate_with_context(
    query: str,
    chunks: list[ChunkHit],
    system_prompt: str | None,
    temperature: float | None,
    max_tokens: int | None,
    llm_override: LLMConfig | None,
    llm_provider_config: dict | None = None,
) -> str:
    """带上下文的 LLM 生成"""
    # 构建上下文
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source_info = f"[来源 {i}]"
        if chunk.metadata.get("title"):
            source_info += f" {chunk.metadata['title']}"
        context_parts.append(f"{source_info}\n{chunk.text}")
    
    context = "\n\n".join(context_parts)
    
    # 构建完整 prompt
    user_prompt = CONTEXT_TEMPLATE.format(context=context, query=query)
    final_system = system_prompt or DEFAULT_RAG_SYSTEM_PROMPT
    
    # 调用 LLM（优先级：llm_override > 租户配置 > 环境变量）
    if llm_override:
        provider_config = llm_override.model_dump()
        provider_config["provider"] = llm_override.provider
        answer = await chat_completion_with_config(
            prompt=user_prompt,
            provider_config=provider_config,
            system_prompt=final_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif llm_provider_config:
        answer = await chat_completion_with_config(
            prompt=user_prompt,
            provider_config=llm_provider_config,
            system_prompt=final_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        answer = await chat_completion(
            prompt=user_prompt,
            system_prompt=final_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    return answer


async def _generate_without_context(
    query: str,
    system_prompt: str | None,
    temperature: float | None,
    max_tokens: int | None,
    llm_override: LLMConfig | None,
    llm_provider_config: dict | None = None,
) -> str:
    """无上下文时的 LLM 生成"""
    no_context_prompt = """你是一个知识库问答助手。用户询问了一个问题，但知识库中没有找到相关信息。
请诚实告知用户这一情况，并尽可能基于你的通用知识提供帮助（但要说明这不是来自知识库的信息）。"""
    
    final_system = system_prompt or no_context_prompt
    
    # 调用 LLM（优先级：llm_override > 租户配置 > 环境变量）
    if llm_override:
        provider_config = llm_override.model_dump()
        provider_config["provider"] = llm_override.provider
        answer = await chat_completion_with_config(
            prompt=query,
            provider_config=provider_config,
            system_prompt=final_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif llm_provider_config:
        answer = await chat_completion_with_config(
            prompt=query,
            provider_config=llm_provider_config,
            system_prompt=final_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        answer = await chat_completion(
            prompt=query,
            system_prompt=final_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    return answer


def _build_response(
    answer: str,
    sources: list[RAGSource],
    retriever_name: str,
    settings,
    llm_override: LLMConfig | None = None,
    embedding_override: dict | None = None,
    rerank_override: dict | None = None,
    retrieval_count: int = 0,
) -> RAGResponse:
    """构建 RAG 响应"""
    # 获取模型配置（优先使用实际使用的配置）
    env_embedding_config = settings.get_embedding_config()
    llm_config = settings.get_llm_config()
    env_rerank_config = settings.get_rerank_config()
    
    # Embedding 配置：优先使用 embedding_override
    if embedding_override:
        embedding_provider = embedding_override.get("provider") or env_embedding_config["provider"]
        embedding_model = embedding_override.get("model") or env_embedding_config["model"]
    else:
        embedding_provider = env_embedding_config["provider"]
        embedding_model = env_embedding_config["model"]
    
    # LLM 配置
    llm_provider = llm_override.provider if llm_override else llm_config["provider"]
    llm_model = llm_override.model if llm_override else llm_config["model"]
    
    # Rerank 配置：优先使用 rerank_override
    if rerank_override:
        rerank_provider = rerank_override.get("provider") or env_rerank_config.get("provider")
        rerank_model = rerank_override.get("model") or env_rerank_config.get("model")
    else:
        rerank_provider = env_rerank_config.get("provider")
        rerank_model = env_rerank_config.get("model")
    
    # 如果 rerank_provider 是 "none" 则设为 None
    if rerank_provider == "none":
        rerank_provider = None
        rerank_model = None
    
    model_info = RAGModelInfo(
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
        retriever=retriever_name,
        rerank_provider=rerank_provider,
        rerank_model=rerank_model,
    )
    
    return RAGResponse(
        answer=answer,
        sources=sources,
        model=model_info,
        retrieval_count=retrieval_count,
    )
