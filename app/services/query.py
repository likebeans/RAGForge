"""
检索服务 (Query Service)

负责知识库检索，是 RAG 的核心组件：
1. 验证知识库权限
2. 向量化查询语句
3. 在向量数据库中搜索
4. Context Window 上下文扩展（可选）
5. 组装返回结果
"""

import time

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline import operator_registry
from app.pipeline.retrievers.dense import DenseRetriever
from app.config import get_settings
from app.pipeline.postprocessors.context_window import (
    ContextWindowPostprocessor,
    ContextWindowConfig,
)
from app.models import Chunk, KnowledgeBase
from app.schemas.internal import RetrieveParams
from app.schemas.query import ChunkHit
from app.db.session import SessionLocal
from app.exceptions import KBConfigError
from app.infra.metrics import metrics_collector
from app.services.acl import UserContext, filter_results_by_acl


async def get_tenant_kbs(session: AsyncSession, tenant_id: str, kb_ids: list[str]) -> list[KnowledgeBase]:
    """
    获取租户的知识库列表
    
    用于验证请求的知识库是否都属于当前租户。
    """
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant_id,
            KnowledgeBase.id.in_(kb_ids),
        )
    )
    return result.scalars().all()


async def retrieve_chunks(
    *,
    tenant_id: str,
    kbs: list[KnowledgeBase],
    params: RetrieveParams,
    session: AsyncSession | None = None,
    user_context: UserContext | None = None,
) -> tuple[list[ChunkHit], str, bool]:
    """
    检索文档片段
    
    核心检索流程：
    1. 将查询语句向量化
    2. 在向量数据库中搜索最相似的片段
    3. （可选）Context Window 上下文扩展
    4. Security Trimming（ACL 权限过滤）
    5. 按相似度分数排序返回
    
    Args:
        tenant_id: 租户 ID（用于数据隔离）
        kbs: 要搜索的知识库列表（已验证）
        params: 检索参数对象，包含查询、检索器、过滤等配置
        session: 数据库会话（用于 Context Window）
        user_context: 用户上下文（用于 ACL 权限过滤）
    
    Returns:
        (list[ChunkHit], retriever_name, acl_blocked): 检索结果列表、使用的检索器名称、是否因 ACL 过滤导致无结果
    """
    retriever_override = params.to_retriever_override_dict()
    retriever, retriever_name = _resolve_retriever(kbs, retriever_override)
    
    # 执行检索并记录指标
    start_time = time.perf_counter()
    raw_hits = await retriever.retrieve(
        query=params.query,
        tenant_id=tenant_id,
        kb_ids=[kb.id for kb in kbs],
        top_k=params.top_k,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    # 记录检索质量指标
    metrics_collector.record_retrieval(
        retriever=retriever_name,
        query=params.query,
        results=raw_hits,
        latency_ms=latency_ms,
    )

    # Context Window 后处理
    context_window = params.context_window
    if context_window is None:
        context_window = ContextWindowConfig()  # 默认启用
    
    if context_window.enabled and session is not None:
        postprocessor = ContextWindowPostprocessor(
            before=context_window.before,
            after=context_window.after,
            max_tokens=context_window.max_tokens,
        )
        raw_hits = await postprocessor.process(raw_hits, session)

    # 父子分块支持：对子片段补充父片段文本作为上下文
    if session is not None:
        raw_hits = await _attach_parent_context(raw_hits, tenant_id=tenant_id, session=session)

    # Rerank 后处理（使用配置的 Rerank 提供商）
    rerank_applied = False
    if params.rerank and raw_hits:
        raw_hits, rerank_applied = await _apply_rerank(
            query=params.query,
            hits=raw_hits,
            top_k=params.rerank_top_k or params.top_k,
        )

    def _metadata_match(hit_meta: dict, filter_meta: dict) -> bool:
        if not filter_meta:
            return True
        for key, expected in filter_meta.items():
            if hit_meta.get(key) != expected:
                return False
        return True

    filtered_hits = []
    for hit in raw_hits:
        score = hit.get("score", 0.0)
        if params.score_threshold is not None and score < params.score_threshold:
            continue
        hit_meta = hit.get("metadata", {}) or {}
        if not _metadata_match(hit_meta, params.metadata_filter or {}):
            continue
        filtered_hits.append(hit)

    # Security Trimming: ACL 权限过滤（二次安全修整）
    # 在向量库过滤的基础上，进行后处理过滤确保权限正确
    has_hits_before_acl = bool(filtered_hits)
    acl_blocked = False
    if user_context is not None:
        filtered_hits = filter_results_by_acl(filtered_hits, user_context)
        if has_hits_before_acl and not filtered_hits:
            acl_blocked = True

    results = [
        ChunkHit(
            chunk_id=hit["chunk_id"],
            text=hit["text"],
            score=hit.get("score", 0.0),
            metadata=hit.get("metadata", {}),
            knowledge_base_id=hit.get("knowledge_base_id"),
            document_id=hit.get("document_id"),
            context_text=hit.get("context_text"),
            context_before=hit.get("context_before"),
            context_after=hit.get("context_after"),
            hyde_queries=hit.get("hyde_queries"),
            hyde_queries_count=hit.get("hyde_queries_count"),
            generated_queries=hit.get("generated_queries"),
            queries_count=hit.get("queries_count"),
            retrieval_details=hit.get("retrieval_details"),
        )
        for hit in filtered_hits
    ]
    return results, retriever_name, acl_blocked


def _resolve_retriever(kbs: list[KnowledgeBase], override: dict | None = None) -> tuple:
    """
    选择检索算子：优先使用 override，否则使用 KB 配置，默认 dense。
    
    Args:
        kbs: 知识库列表
        override: 检索器覆盖配置，格式 {"name": "hyde", "params": {...}}
    
    Returns:
        (retriever, retriever_name): 检索器实例和名称
    """
    name = "dense"
    params: dict = {}
    allow_mixed = False
    embedding_config: dict | None = None
    
    # 从知识库配置中提取 embedding 配置
    if kbs:
        embedding_config = _extract_embedding_config(kbs)
    
    # 优先使用 override
    if override:
        name = override.get("name", "dense")
        params = override.get("params", {}) or {}
    elif kbs:
        name, params, allow_mixed = _validate_retriever_config(kbs)
    
    # 将 embedding_config 传递给检索器
    if embedding_config:
        if name in ("dense", "hybrid", "fusion", "llama_dense"):
            # 这些检索器直接接受 embedding_config 参数
            params["embedding_config"] = embedding_config
        elif name in ("hyde", "multi_query"):
            # 这些检索器通过 base_retriever_params 传递给底层检索器
            base_params = params.get("base_retriever_params", {}) or {}
            base_params["embedding_config"] = embedding_config
            params["base_retriever_params"] = base_params

    factory = operator_registry.get("retriever", name)
    if not factory:
        return DenseRetriever(embedding_config=embedding_config), "dense"
    retriever = factory(**params)
    retriever.allow_mixed = allow_mixed if hasattr(retriever, "allow_mixed") else allow_mixed
    return retriever, name


def _extract_embedding_config(kbs: list[KnowledgeBase]) -> dict | None:
    """
    从知识库配置中提取 embedding 配置。
    
    知识库配置中的 embedding 配置格式：
    {
        "embedding": {
            "provider": "ollama",
            "model": "bge-m3:latest"
        }
    }
    """
    if not kbs:
        return None
    
    # 使用第一个知识库的配置
    first_config = kbs[0].config or {}
    embedding_cfg = first_config.get("embedding", {})
    
    if not embedding_cfg:
        return None
    
    provider = embedding_cfg.get("provider")
    model = embedding_cfg.get("model")
    
    if not provider or not model:
        return None
    
    try:
        settings = get_settings()
        return settings._get_provider_config(provider, model)
    except ValueError:
        # 配置不存在，回退到默认配置
        return None


def _validate_retriever_config(kbs: list[KnowledgeBase]) -> tuple[str, dict, bool]:
    """确保多 KB 的 retriever 配置一致，返回 (name, params, allow_mixed)。"""
    name = "dense"
    params: dict = {}
    allow_mixed = False
    first = kbs[0].config or {}
    retr_cfg = first.get("query", {}).get("retriever", {}) if isinstance(first, dict) else {}
    if isinstance(retr_cfg, dict):
        name = retr_cfg.get("name", name)
        params = retr_cfg.get("params", {}) or {}
        allow_mixed = bool(retr_cfg.get("allow_mixed", False))

    for kb in kbs[1:]:
        cfg = kb.config or {}
        r = cfg.get("query", {}).get("retriever", {}) if isinstance(cfg, dict) else {}
        if isinstance(retr_cfg, dict):
            r_name = r.get("name", name)
            r_params = r.get("params", {}) or {}
            r_allow = bool(r.get("allow_mixed", False))
            allow_mixed = allow_mixed or r_allow
            if r_name != name or r_params != params:
                if not allow_mixed:
                    raise KBConfigError(f"多个知识库检索配置不一致: {kb.id}")
    return name, params, allow_mixed


async def _attach_parent_context(raw_hits: list[dict], *, tenant_id: str, session: AsyncSession) -> list[dict]:
    """
    对含 parent_id 的子片段，查询父片段文本并填入 context_text。
    """
    parent_ids = {
        (hit.get("metadata") or {}).get("parent_id")
        for hit in raw_hits
        if (hit.get("metadata") or {}).get("parent_id")
    }
    if not parent_ids:
        return raw_hits

    # 使用 PostgreSQL JSON 操作符 ->> 提取文本值
    from sqlalchemy import cast, String
    result = await session.execute(
        select(Chunk).where(
            Chunk.tenant_id == tenant_id,
            cast(Chunk.extra_metadata["parent_id"], String).in_(parent_ids),
            or_(
                Chunk.extra_metadata["child"].is_(None),
                cast(Chunk.extra_metadata["child"], String) == "false",
            ),
        )
    )
    parent_map = {
        ch.extra_metadata.get("parent_id"): ch
        for ch in result.scalars().all()
        if ch.extra_metadata
    }

    enriched = []
    for hit in raw_hits:
        meta = hit.get("metadata") or {}
        parent_id = meta.get("parent_id")
        if parent_id and parent_id in parent_map:
            parent_chunk = parent_map[parent_id]
            hit = {**hit, "context_text": parent_chunk.text}
        enriched.append(hit)
    return enriched


async def _apply_rerank(
    query: str,
    hits: list[dict],
    top_k: int,
) -> tuple[list[dict], bool]:
    """
    应用 Rerank 后处理
    
    Args:
        query: 原始查询
        hits: 检索结果
        top_k: 返回数量
    
    Returns:
        (reranked_hits, applied): 重排结果和是否成功应用
    """
    import logging
    from app.infra.rerank import rerank_results
    
    logger = logging.getLogger(__name__)
    
    if not hits:
        return hits, False
    
    documents = [hit["text"] for hit in hits]
    
    try:
        reranked = await rerank_results(
            query=query,
            documents=documents,
            top_k=top_k,
        )
        
        # 根据 rerank 结果重排原始 hits
        result = []
        for r in reranked:
            idx = r["index"]
            if idx < len(hits):
                hit = hits[idx].copy()
                hit["score"] = r["score"]
                hit["source"] = hit.get("source", "unknown") + "+rerank"
                result.append(hit)
        
        logger.info(f"Rerank 完成: {len(hits)} -> {len(result)} 条结果")
        return result, True
        
    except Exception as e:
        logger.warning(f"Rerank 失败，返回原始结果: {e}")
        return hits[:top_k], False


async def collect_chunks_for_kbs(tenant_id: str, kb_ids: list[str], limit: int | None = None) -> list[dict]:
    """
    辅助函数：用于 LlamaIndex BM25/Hybrid，从数据库中读取指定 KB 的 chunk 文本/元数据。
    """
    from sqlalchemy import select
    from app.models import Chunk

    async with SessionLocal() as session:
        result = await session.execute(
            select(Chunk).where(
                Chunk.tenant_id == tenant_id,
                Chunk.knowledge_base_id.in_(kb_ids),
            )
        )
        chunks = result.scalars().all()
        if limit is not None and len(chunks) > limit:
            chunks = chunks[:limit]
        return [
            {
                "chunk_id": ch.id,
                "text": ch.text,
                "metadata": (ch.extra_metadata or {}) | {"knowledge_base_id": ch.knowledge_base_id},
            }
            for ch in chunks
        ]
