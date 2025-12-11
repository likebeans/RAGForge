"""
Pipeline / Playground API

用于前端可视化 RAG 各阶段的实验接口。
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import APIKeyContext, get_current_api_key, get_db_session, get_tenant
from app.pipeline import chunkers, retrievers  # noqa: F401  # 触发 import 侧注册
from app.pipeline.registry import operator_registry
from app.schemas.pipeline import (
    ChunkPreview,
    OperatorListResponse,
    OperatorMeta,
    PlaygroundRunRequest,
    PlaygroundRunResponse,
    QueryTransformPreview,
    RagPreview,
    RetrievalPreview,
)
from app.schemas.query import ChunkHit
from app.schemas.rag import RAGModelInfo
from app.schemas.internal import RAGParams, RetrieveParams
from app.services.query import get_tenant_kbs, retrieve_chunks
from app.services.rag import generate_rag_response

router = APIRouter(prefix="/v1/pipeline", tags=["pipeline"])


# ===== 算子元数据 =====

_STATIC_QUERY_TRANSFORMS = [
    OperatorMeta(
        kind="query_transform",
        name="hyde",
        label="HyDE",
        description="假设文档生成查询",
    ),
    OperatorMeta(
        kind="query_transform",
        name="rag_fusion",
        label="RAG-Fusion",
        description="多查询扩展与融合",
    ),
]

_STATIC_ENRICHERS = [
    OperatorMeta(
        kind="enricher",
        name="chunk_enricher",
        label="Chunk Enricher",
        description="为 Chunk 补充上下文字段",
    ),
    OperatorMeta(
        kind="enricher",
        name="summarizer",
        label="Document Summarizer",
        description="文档摘要生成",
    ),
]

_STATIC_POSTPROCESSORS = [
    OperatorMeta(
        kind="postprocessor",
        name="context_window",
        label="Context Window",
        description="检索结果前后文扩展",
    ),
]


def _build_operator_meta(kind: str, name: str, cls: Any) -> OperatorMeta:
    doc = (getattr(cls, "__doc__", None) or "").strip().splitlines()
    desc = doc[0] if doc else ""
    return OperatorMeta(
        kind=kind,
        name=name,
        label=name.replace("_", " ").title(),
        description=desc,
        params_schema=None,
    )


@router.get("/operators", response_model=OperatorListResponse)
async def list_operators(
    _: APIKeyContext = Depends(get_current_api_key),
):
    """列出可用的 chunker / retriever 等算子，供前端生成配置。"""
    chunker_names = operator_registry.list("chunker")
    retriever_names = operator_registry.list("retriever")

    chunkers_meta = []
    for name in chunker_names:
        cls = operator_registry.get("chunker", name)
        if cls:
            chunkers_meta.append(_build_operator_meta("chunker", name, cls))

    retrievers_meta = []
    for name in retriever_names:
        cls = operator_registry.get("retriever", name)
        if cls:
            retrievers_meta.append(_build_operator_meta("retriever", name, cls))

    return OperatorListResponse(
        chunkers=chunkers_meta,
        retrievers=retrievers_meta,
        query_transforms=_STATIC_QUERY_TRANSFORMS,
        enrichers=_STATIC_ENRICHERS,
        postprocessors=_STATIC_POSTPROCESSORS,
    )


# ===== Playground 运行 =====


@router.post("/playground/run", response_model=PlaygroundRunResponse)
async def run_playground(
    payload: PlaygroundRunRequest,
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """运行一次可视化 RAG 实验，返回各阶段的中间结果。"""
    # 验证知识库
    kbs = await get_tenant_kbs(db, tenant_id=tenant.id, kb_ids=payload.knowledge_base_ids)
    if len(kbs) != len(set(payload.knowledge_base_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "One or more knowledge bases not found for tenant"},
        )

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
                    "detail": f"API Key 无权访问以下知识库: {list(unauthorized_kbs)}"
                },
            )

    # 可选：切分预览
    chunk_preview = None
    if payload.chunk_preview_text and payload.chunker:
        chunk_preview = await _run_chunk_preview(
            name=payload.chunker,
            text=payload.chunk_preview_text,
            params=payload.chunker_params or {},
        )

    # 检索阶段
    retrieve_params = RetrieveParams(
        query=payload.query,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        retriever_override=payload.retriever,
        rerank=payload.rerank,
        rerank_top_k=payload.rerank_top_k,
        rerank_override=payload.rerank_override,
    )

    user_context = api_key_ctx.get_user_context()

    start_retrieve = time.perf_counter()
    results, retriever_name, acl_blocked = await retrieve_chunks(
        tenant_id=tenant.id,
        kbs=kbs,
        params=retrieve_params,
        session=db,
        user_context=user_context,
    )
    retrieve_latency = (time.perf_counter() - start_retrieve) * 1000

    if acl_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NO_PERMISSION", "detail": "检索结果已被权限控制过滤，请检查文档敏感度或 API Key 权限"},
        )

    # RAG 阶段
    rag_params = RAGParams(
        query=payload.query,
        kb_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        retriever_override=payload.retriever,
        llm_override=payload.llm_override,
    )

    start_rag = time.perf_counter()
    rag_resp = await generate_rag_response(
        session=db,
        tenant_id=tenant.id,
        params=rag_params,
        user_context=user_context,
    )
    rag_latency = (time.perf_counter() - start_rag) * 1000

    query_transform_info = _extract_query_transform(results, payload.query)

    retrieval_preview = RetrievalPreview(
        retriever=retriever_name,
        latency_ms=retrieve_latency,
        rerank_applied=payload.rerank,
        results=results,
    )

    rag_preview = RagPreview(
        answer=rag_resp.answer,
        sources=[ChunkHit(**src.model_dump()) for src in rag_resp.sources],
        model=RAGModelInfo(**rag_resp.model.model_dump()),
        latency_ms=rag_latency,
    )

    metrics = {
        "retrieve_ms": round(retrieve_latency, 2),
        "rag_ms": round(rag_latency, 2),
        "total_ms": round(retrieve_latency + rag_latency, 2),
    }

    return PlaygroundRunResponse(
        query=payload.query,
        knowledge_base_ids=payload.knowledge_base_ids,
        chunk_preview=chunk_preview,
        query_transform=query_transform_info,
        retrieval=retrieval_preview,
        rag=rag_preview,
        metrics=metrics,
    )


async def _run_chunk_preview(name: str, text: str, params: dict[str, Any]) -> list[ChunkPreview]:
    """使用指定切分器对文本进行预览切分。"""
    cls = operator_registry.get("chunker", name)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CHUNKER_NOT_FOUND", "detail": f"未找到切分器: {name}"},
        )
    try:
        chunker = cls(**params) if params else cls()
    except Exception as e:  # pragma: no cover - 转化为用户错误提示
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CHUNKER_INIT_FAILED", "detail": str(e)},
        )

    pieces = chunker.chunk(text=text, metadata={})
    previews: list[ChunkPreview] = []
    for idx, piece in enumerate(pieces):
        previews.append(
            ChunkPreview(
                chunk_id=str(idx),
                text=piece.text,
                metadata=piece.metadata,
            )
        )
    return previews


def _extract_query_transform(results: list[ChunkHit], original_query: str) -> QueryTransformPreview | None:
    """从检索结果中提取查询增强信息（如 HyDE/multi-query）。"""
    hyde_prompts: list[str] = []
    generated_queries: list[str] = []
    for hit in results:
        if hit.hyde_queries:
            hyde_prompts.extend(hit.hyde_queries)
        if hit.generated_queries:
            generated_queries.extend(hit.generated_queries)

    if not hyde_prompts and not generated_queries:
        return None

    return QueryTransformPreview(
        original_query=original_query,
        generated_queries=list({q for q in generated_queries if q}),
        hyde_prompts=list({p for p in hyde_prompts if p}),
    )
