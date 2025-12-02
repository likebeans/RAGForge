"""
文档摄取服务 (Ingestion Service)

负责将用户上传的文档处理并存入知识库：
1. 文本切分（Chunking）
2. 向量化（Embedding）
3. 存储到向量数据库
4. 保存元数据到 PostgreSQL
5. （可选）生成文档摘要
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.vector_store import vector_store
from app.infra.bm25_store import bm25_store
from app.infra.llamaindex import build_index_by_store, nodes_from_chunks
from app.models import Chunk, Document, KnowledgeBase
from app.pipeline import operator_registry
from app.pipeline.base import BaseChunkerOperator
from app.pipeline.chunkers.simple import SimpleChunker
from app.pipeline.enrichers.summarizer import generate_summary, SummaryConfig
from app.pipeline.enrichers.chunk_enricher import get_chunk_enricher, EnrichmentConfig

logger = logging.getLogger(__name__)


async def ensure_kb_belongs_to_tenant(
    session: AsyncSession,
    kb_id: str,
    tenant_id: str,
) -> KnowledgeBase:
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant_id,
        )
    )
    kb = result.scalar_one_or_none()
    return kb


async def ingest_document(
    session: AsyncSession,
    *,
    tenant_id: str,
    kb: KnowledgeBase,
    title: str,
    content: str,
    metadata: dict | None,
    source: str | None,
    generate_doc_summary: bool = True,
    enrich_chunks: bool = False,
) -> tuple[Document, list[Chunk]]:
    """
    摄取文档
    
    Args:
        session: 数据库会话
        tenant_id: 租户 ID
        kb: 知识库
        title: 文档标题
        content: 文档内容
        metadata: 扩展元数据
        source: 来源类型
        generate_doc_summary: 是否生成文档摘要（默认 True）
        enrich_chunks: 是否增强 chunks（默认 False，需显式开启）
    """
    chunker = _resolve_chunker(kb)

    doc = Document(
        tenant_id=tenant_id,
        knowledge_base_id=kb.id,
        title=title,
        extra_metadata=metadata or {},
        source=source,
        summary_status="pending",
    )
    session.add(doc)
    await session.flush()
    
    # 异步生成文档摘要（不阻塞主流程）
    if generate_doc_summary:
        await _generate_document_summary(doc, content)

    chunk_pieces = chunker.chunk(content, metadata=metadata or {})
    chunks: list[Chunk] = []
    for idx, piece in enumerate(chunk_pieces):
        # 添加 chunk_index 到 metadata，用于 Context Window 扩展
        piece_metadata = (piece.metadata or {}).copy()
        piece_metadata["chunk_index"] = idx
        piece_metadata["total_chunks"] = len(chunk_pieces)
        
        chunk = Chunk(
            tenant_id=tenant_id,
            knowledge_base_id=kb.id,
            document_id=doc.id,
            text=piece.text,
            extra_metadata=piece_metadata,
            indexing_status="pending",
            indexing_retry_count=0,
        )
        session.add(chunk)
        chunks.append(chunk)

    await session.flush()
    
    # Chunk Enrichment（可选，默认关闭）
    if enrich_chunks:
        await _enrich_chunks(chunks, doc)

    store_cfg = _get_store_config(kb)
    skip_qdrant = store_cfg.get("skip_qdrant", False)

    # 标记所有 chunks 为 indexing 状态
    for chunk in chunks:
        chunk.indexing_status = "indexing"
    await session.flush()

    # 批量写入向量库（异步，带错误处理）
    indexing_error = None
    if not skip_qdrant:
        chunk_data = [
            {
                "chunk_id": chunk.id,
                "knowledge_base_id": kb.id,
                "text": chunk.text,
                "metadata": {
                    "document_id": doc.id,
                    "title": doc.title,
                    "source": source,
                } | (metadata or {}),
            }
            for chunk in chunks
        ]
        try:
            await vector_store.upsert_chunks(tenant_id=tenant_id, chunks=chunk_data)
        except Exception as e:
            indexing_error = str(e)
            logger.error(f"向量库写入失败: {e}")
    
    # 写入 BM25 索引（同步，内存操作）
    bm25_store.upsert_chunks(
        tenant_id=tenant_id,
        knowledge_base_id=kb.id,
        chunks=[
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "metadata": {
                    "document_id": doc.id,
                    "title": doc.title,
                    "source": source,
                }
                | (metadata or {}),
            }
            for chunk in chunks
        ],
    )

    # 更新索引状态
    for chunk in chunks:
        if indexing_error:
            chunk.indexing_status = "failed"
            chunk.indexing_error = indexing_error
            chunk.indexing_retry_count += 1
        else:
            chunk.indexing_status = "indexed"
            chunk.indexing_error = None

    _maybe_upsert_llamaindex(store_config=store_cfg, kb=kb, tenant_id=tenant_id, chunks=chunks)

    return doc, chunks


async def retry_failed_chunks(
    session: AsyncSession,
    *,
    tenant_id: str,
    max_retries: int = 3,
    batch_size: int = 100,
) -> dict[str, int]:
    """
    重试失败的 chunk 索引
    
    Args:
        session: 数据库会话
        tenant_id: 租户 ID
        max_retries: 最大重试次数
        batch_size: 每批处理数量
    
    Returns:
        {"success": N, "failed": M, "skipped": K}
    """
    from sqlalchemy import select, and_
    
    # 查询失败且未超过重试次数的 chunks
    result = await session.execute(
        select(Chunk).where(
            and_(
                Chunk.tenant_id == tenant_id,
                Chunk.indexing_status == "failed",
                Chunk.indexing_retry_count < max_retries,
            )
        ).limit(batch_size)
    )
    failed_chunks = list(result.scalars().all())
    
    if not failed_chunks:
        return {"success": 0, "failed": 0, "skipped": 0}
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    # 按知识库分组
    kb_chunks: dict[str, list[Chunk]] = {}
    for chunk in failed_chunks:
        kb_chunks.setdefault(chunk.knowledge_base_id, []).append(chunk)
    
    for kb_id, chunks in kb_chunks.items():
        # 标记为 indexing
        for chunk in chunks:
            chunk.indexing_status = "indexing"
        await session.flush()
        
        # 尝试写入向量库
        chunk_data = [
            {
                "chunk_id": chunk.id,
                "knowledge_base_id": chunk.knowledge_base_id,
                "text": chunk.text,
                "metadata": chunk.extra_metadata or {},
            }
            for chunk in chunks
        ]
        
        try:
            await vector_store.upsert_chunks(tenant_id=tenant_id, chunks=chunk_data)
            # 成功
            for chunk in chunks:
                chunk.indexing_status = "indexed"
                chunk.indexing_error = None
            stats["success"] += len(chunks)
        except Exception as e:
            # 失败
            for chunk in chunks:
                chunk.indexing_status = "failed"
                chunk.indexing_error = str(e)
                chunk.indexing_retry_count += 1
                if chunk.indexing_retry_count >= max_retries:
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1
            logger.error(f"重试索引失败 (kb={kb_id}): {e}")
    
    return stats


def _resolve_chunker(kb: KnowledgeBase) -> BaseChunkerOperator:
    cfg = kb.config or {}
    chunker_cfg = cfg.get("ingestion", {}).get("chunker", {}) if isinstance(cfg, dict) else {}
    name = chunker_cfg.get("name", "simple")
    params = chunker_cfg.get("params", {}) if isinstance(chunker_cfg, dict) else {}

    factory = operator_registry.get("chunker", name)
    if not factory:
        return SimpleChunker(**params) if params else SimpleChunker()
    return factory(**params)


def _get_store_config(kb: KnowledgeBase) -> dict:
    cfg = kb.config or {}
    ingestion = cfg.get("ingestion", {}) if isinstance(cfg, dict) else {}
    store_cfg = ingestion.get("store", {}) if isinstance(ingestion.get("store"), dict) else {}
    return store_cfg


def _maybe_upsert_llamaindex(store_config: dict, kb: KnowledgeBase, tenant_id: str, chunks: list[Chunk]) -> None:
    store_type = store_config.get("type", "qdrant").lower()
    params = store_config.get("params", {}) if isinstance(store_config.get("params"), dict) else {}
    # qdrant 已通过 vector_store 写入，可跳过
    if store_type == "qdrant":
        return
    try:
        index = build_index_by_store(store_type, tenant_id=tenant_id, kb_id=kb.id, params=params)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"llamaindex upsert failed for store={store_type}: {exc}") from exc
    nodes = nodes_from_chunks(
        chunks=[
            {
                "chunk_id": ch.id,
                "text": ch.text,
                "metadata": (ch.extra_metadata or {}) | {"knowledge_base_id": kb.id, "document_id": ch.document_id},
            }
            for ch in chunks
        ]
    )
    index.insert_nodes(nodes)


async def _generate_document_summary(doc: Document, content: str) -> None:
    """
    生成文档摘要（异步）
    
    生成成功后更新 doc.summary 和 doc.summary_status
    失败时设置 summary_status = "failed"
    文档太短时设置 summary_status = "skipped"
    """
    try:
        doc.summary_status = "generating"
        
        summary = await generate_summary(content)
        
        if summary:
            doc.summary = summary
            doc.summary_status = "completed"
            logger.info(f"文档 {doc.id} 摘要生成成功")
        else:
            doc.summary_status = "skipped"
            logger.info(f"文档 {doc.id} 跳过摘要生成（内容太短或未配置）")
            
    except Exception as e:
        doc.summary_status = "failed"
        logger.warning(f"文档 {doc.id} 摘要生成失败: {e}")


async def _enrich_chunks(chunks: list[Chunk], doc: Document) -> None:
    """
    批量增强 chunks（异步）
    
    遍历 chunks，调用 ChunkEnricher 生成增强文本，
    更新 chunk.enriched_text 和 chunk.enrichment_status
    """
    enricher = get_chunk_enricher()
    if enricher is None:
        logger.info("Chunk Enrichment 未启用或未配置")
        for chunk in chunks:
            chunk.enrichment_status = "skipped"
        return
    
    try:
        # 准备 chunk 数据
        chunk_data = [
            {
                "text": chunk.text,
                "chunk_index": (chunk.extra_metadata or {}).get("chunk_index", i),
            }
            for i, chunk in enumerate(chunks)
        ]
        
        # 批量增强
        enriched_results = await enricher.enrich_chunks(
            chunks=chunk_data,
            doc_title=doc.title,
            doc_summary=doc.summary,
        )
        
        # 更新 chunks
        for chunk, result in zip(chunks, enriched_results):
            chunk.enriched_text = result.get("enriched_text")
            chunk.enrichment_status = result.get("enrichment_status", "failed")
        
        completed = sum(1 for c in chunks if c.enrichment_status == "completed")
        logger.info(f"文档 {doc.id} Chunk Enrichment 完成: {completed}/{len(chunks)}")
        
    except Exception as e:
        logger.warning(f"文档 {doc.id} Chunk Enrichment 失败: {e}")
        for chunk in chunks:
            chunk.enrichment_status = "failed"
