"""
检索服务 (Query Service)

负责知识库检索，是 RAG 的核心组件：
1. 验证知识库权限
2. 向量化查询语句
3. 在向量数据库中搜索
4. Context Window 上下文扩展（可选）
5. 组装返回结果
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline import operator_registry
from app.pipeline.retrievers.dense import DenseRetriever
from app.pipeline.postprocessors.context_window import (
    ContextWindowPostprocessor,
    ContextWindowConfig,
)
from app.models import Chunk, KnowledgeBase
from app.schemas.query import ChunkHit
from app.db.session import SessionLocal
from app.exceptions import KBConfigError


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
    query: str,
    top_k: int,
    session: AsyncSession | None = None,
    context_window: ContextWindowConfig | None = None,
    score_threshold: float | None = None,
    metadata_filter: dict | None = None,
) -> list[ChunkHit]:
    """
    检索文档片段
    
    核心检索流程：
    1. 将查询语句向量化
    2. 在向量数据库中搜索最相似的片段
    3. （可选）Context Window 上下文扩展
    4. 按相似度分数排序返回
    
    Args:
        tenant_id: 租户 ID（用于数据隔离）
        kbs: 要搜索的知识库列表
        query: 查询语句
        top_k: 返回结果数量
        session: 数据库会话（用于 Context Window）
        context_window: 上下文窗口配置，None 表示使用默认配置（启用）
    
    Returns:
        list[ChunkHit]: 检索结果列表，按相似度降序
    """
    retriever = _resolve_retriever(kbs)
    raw_hits = await retriever.retrieve(
        query=query,
        tenant_id=tenant_id,
        kb_ids=[kb.id for kb in kbs],
        top_k=top_k,
    )

    # Context Window 后处理
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
        if score_threshold is not None and score < score_threshold:
            continue
        hit_meta = hit.get("metadata", {}) or {}
        if not _metadata_match(hit_meta, metadata_filter or {}):
            continue
        filtered_hits.append(hit)

    return [
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
        )
        for hit in filtered_hits
    ]


def _resolve_retriever(kbs: list[KnowledgeBase]):
    """
    选择检索算子：若 KB 配置存在 query.retriever，则优先使用第一个 KB 的配置；否则默认 dense。
    如果多个 KB 配置不一致，将抛出 KBConfigError。
    """
    name = "dense"
    params: dict = {}
    allow_mixed = False
    if kbs:
        name, params, allow_mixed = _validate_retriever_config(kbs)

    factory = operator_registry.get("retriever", name)
    if not factory:
        return DenseRetriever(**params)
    retriever = factory(**params)
    retriever.allow_mixed = allow_mixed if hasattr(retriever, "allow_mixed") else allow_mixed
    return retriever


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

    result = await session.execute(
        select(Chunk).where(
            Chunk.tenant_id == tenant_id,
            Chunk.extra_metadata["parent_id"].astext.in_(parent_ids),
            or_(
                Chunk.extra_metadata["child"].astext.is_(None),
                Chunk.extra_metadata["child"].astext == "false",
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
