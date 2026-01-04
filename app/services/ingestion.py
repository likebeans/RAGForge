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
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.vector_store import vector_store
from app.infra.bm25_store import bm25_store
from app.infra.bm25_cache import get_bm25_cache
from app.infra.llamaindex import build_index_by_store, nodes_from_chunks
from app.models import Chunk, Document, KnowledgeBase
from app.pipeline import operator_registry
from app.schemas.internal import IngestionParams
from app.pipeline.base import BaseChunkerOperator
from app.pipeline.chunkers.simple import SimpleChunker
from app.pipeline.enrichers.summarizer import generate_summary, SummaryConfig, resolve_summary_preset
from app.pipeline.enrichers.chunk_enricher import get_chunk_enricher, EnrichmentConfig
from app.pipeline.indexers.raptor import (
    RaptorNativeIndexer,
    create_raptor_native_indexer_from_config,
    RAPTOR_NATIVE_AVAILABLE,
)
from app.services.acl import build_acl_metadata_for_chunk

logger = logging.getLogger(__name__)


def _is_parent_chunk(metadata: dict) -> bool:
    """
    判断是否为父块（用于父子分块模式）
    
    父块特征：有 parent_id 但没有 child 标记或 child=False
    子块特征：有 parent_id 且 child=True
    普通块：没有 parent_id
    
    只有子块需要被向量化，父块只存 DB 作为上下文。
    """
    parent_id = metadata.get("parent_id")
    if not parent_id:
        return False  # 普通块，需要向量化
    
    # 有 parent_id 的情况：检查是否是子块
    is_child = metadata.get("child", False)
    if isinstance(is_child, str):
        is_child = is_child.lower() == "true"
    
    # 父块 = 有 parent_id 但不是 child
    return not is_child


def _resolve_embedding_config_from_kb(kb: KnowledgeBase) -> dict | None:
    """
    从知识库配置解析 Embedding 配置（兼容 embedding.* 与旧版扁平字段）。
    """
    cfg = kb.config or {}
    if not isinstance(cfg, dict):
        return None

    embedding_cfg = cfg.get("embedding") if isinstance(cfg.get("embedding"), dict) else {}
    provider = embedding_cfg.get("provider") or cfg.get("embedding_provider")
    model = embedding_cfg.get("model") or cfg.get("embedding_model")
    dim = embedding_cfg.get("dim")
    if dim is None:
        dim = cfg.get("embedding_dim")

    if not provider or not model:
        return None

    try:
        from app.config import get_settings
        settings = get_settings()
        provider_config = settings._get_provider_config(provider, model)
        if dim is not None:
            provider_config["dim"] = dim
        return provider_config
    except Exception as exc:
        logger.warning("知识库 Embedding 配置无效: %s/%s (%s)", provider, model, exc)
        return None


def _resolve_summary_config(enricher_config: dict | None) -> SummaryConfig | None:
    """
    从增强器配置解析摘要长度配置（仅 document_summary 生效）。
    """
    if not enricher_config or enricher_config.get("name") != "document_summary":
        return None

    params = enricher_config.get("params") or {}
    summary_length = params.get("summary_length")
    if not summary_length:
        return None

    max_tokens, length_hint = resolve_summary_preset(summary_length)
    if not max_tokens:
        return None

    from app.config import get_settings
    settings = get_settings()
    return SummaryConfig(
        enabled=True,
        min_tokens=settings.doc_summary_min_tokens,
        max_tokens=max_tokens,
        model=settings.doc_summary_model,
        length_hint=length_hint,
    )


@dataclass
class IndexingResult:
    """
    多后端写入结果
    
    用于结构化返回各向量存储后端的写入状态，
    替代简单的日志打印，便于上层处理和告警。
    """
    store_type: str
    success: bool
    chunks_count: int = 0
    error: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "store_type": self.store_type,
            "success": self.success,
            "chunks_count": self.chunks_count,
            "error": self.error,
        }


@dataclass
class IngestionResult:
    """
    文档摄取结果
    
    包含主存储（Qdrant）和可选的多后端存储（Milvus/ES）的写入状态。
    """
    document: "Document"
    chunks: list["Chunk"]
    indexing_results: list[IndexingResult] = field(default_factory=list)
    
    @property
    def all_success(self) -> bool:
        """所有后端写入是否都成功"""
        return all(r.success for r in self.indexing_results)
    
    @property
    def primary_success(self) -> bool:
        """主存储（qdrant）是否写入成功"""
        for r in self.indexing_results:
            if r.store_type == "qdrant":
                return r.success
        return True  # 如果没有 qdrant 结果，认为成功
    
    def failed_stores(self) -> list[IndexingResult]:
        """获取失败的后端列表"""
        return [r for r in self.indexing_results if not r.success]


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
    params: IngestionParams,
    embedding_config: dict | None = None,
) -> IngestionResult:
    """
    摄取文档
    
    Args:
        session: 数据库会话
        tenant_id: 租户 ID
        kb: 知识库（已验证）
        params: 摄取参数对象，包含标题、内容、元数据等配置
        embedding_config: 可选的 embedding 配置（来自前端），格式为 {provider, model, api_key, base_url}
    
    Returns:
        IngestionResult: 包含文档、chunks 和各后端写入状态的结果对象
    """
    import time
    from datetime import datetime
    ingest_start = time.time()
    
    # 处理日志缓冲区
    log_lines: list[str] = []
    # 步骤进度信息（用于前端解析）
    steps_info: list[dict] = []
    # 用于保存日志的文档引用（在获取到 doc 后设置）
    doc_ref: list = []  # 使用列表来存储引用，便于在闭包中修改
    
    async def save_log_to_db():
        """将日志实时保存到数据库（使用 commit 确保其他会话可见）"""
        if doc_ref:
            doc_ref[0].processing_log = "\n".join(log_lines)
            await session.commit()
    
    def add_log(msg: str, level: str = "INFO"):
        from zoneinfo import ZoneInfo
        from app.config import get_settings
        tz = ZoneInfo(get_settings().timezone)
        ts = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        log_lines.append(f"[{ts}] [{level}] {msg}")
        if level == "ERROR":
            logger.error(msg)
        elif level == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)
    
    async def add_step(step_num: int, total: int, label: str, status: str = "running"):
        """添加步骤进度信息并保存到数据库"""
        steps_info.append({"step": step_num, "total": total, "label": label, "status": status})
        add_log(f"[STEP:{step_num}/{total}:{status}] {label}")
        await save_log_to_db()
    
    async def update_step(step_num: int, status: str):
        """更新步骤状态并保存到数据库"""
        total = 6  # 默认总步骤数
        for s in steps_info:
            if s["step"] == step_num:
                s["status"] = status
                total = s["total"]
                break
        add_log(f"[STEP:{step_num}/{total}:{status}]")
        await save_log_to_db()
    
    async def check_interrupted() -> bool:
        """检查文档是否被用户中断，返回 True 表示已中断"""
        if not doc_ref:
            return False
        # 从数据库重新读取文档状态（使用新查询避免缓存）
        result = await session.execute(
            select(Document.processing_status).where(Document.id == doc_ref[0].id)
        )
        current_status = result.scalar_one_or_none()
        if current_status == "interrupted":
            add_log("检测到用户中断请求，停止处理", level="WARNING")
            await save_log_to_db()
            return True
        return False
    
    add_log(f"开始处理文档: {params.title}")

    if embedding_config is None:
        embedding_config = _resolve_embedding_config_from_kb(kb)
        if embedding_config:
            add_log(
                f"使用知识库 Embedding 配置: {embedding_config.get('provider')}/{embedding_config.get('model')}"
            )
    
    # 支持使用已存在的文档记录（用于后台异步入库场景）
    # 先获取 doc，这样后续步骤的日志才能实时保存
    if params.existing_doc_id:
        doc_result = await session.execute(
            select(Document).where(Document.id == params.existing_doc_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"文档 {params.existing_doc_id} 不存在")
        doc_ref.append(doc)  # 设置文档引用，便于实时保存日志
        # 读取已有的处理日志（在后台任务中可能已经设置了初始日志）
        if doc.processing_log:
            log_lines.extend(doc.processing_log.split("\n"))
        add_log(f"使用已存在的文档记录: doc_id={doc.id}")
        # 设置状态为处理中
        doc.processing_status = "processing"
        await save_log_to_db()
    
    await add_step(1, 6, "解析切分器配置", "running")
    chunker = _resolve_chunker(kb)
    add_log(f"使用切分器: {type(chunker).__name__}")
    await update_step(1, "done")

    await add_step(2, 6, "创建文档记录", "running")
    
    if not params.existing_doc_id:
        doc = Document(
            tenant_id=tenant_id,
            knowledge_base_id=kb.id,
            title=params.title,
            extra_metadata=params.metadata or {},
            source=params.source,
            summary_status="pending",
            # ACL 字段（模型中属性名为 acl_allow_*）
            sensitivity_level=params.sensitivity_level,
            acl_allow_users=params.acl_users,
            acl_allow_roles=params.acl_roles,
            acl_allow_groups=params.acl_groups,
        )
        doc.processing_status = "processing"  # 设置状态为处理中
        session.add(doc)
        await session.flush()
        doc_ref.append(doc)  # 设置文档引用
        add_log(f"文档记录创建完成: doc_id={doc.id}")
    
    await update_step(2, "done")
    
    # 异步生成文档摘要（不阻塞主流程）
    if params.generate_doc_summary:
        add_log("生成文档摘要...")
        summary_config = _resolve_summary_config(params.enricher_config)
        await _generate_document_summary(doc, params.content, summary_config=summary_config)

    await add_step(3, 6, "切分文档内容", "running")
    chunk_pieces = chunker.chunk(params.content, metadata=params.metadata or {})
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
    add_log(f"切分完成: 生成 {len(chunks)} 个 chunks")
    await update_step(3, "done")
    
    # 中断检查点 1：切分完成后
    if await check_interrupted():
        return IngestionResult(document=doc, chunks=chunks, indexing_results=[])
    
    # Chunk Enrichment（可选，默认关闭）
    if params.enrich_chunks:
        await add_step(4, 6, "Chunk 上下文增强", "running")
        await _enrich_chunks(
            chunks, doc,
            llm_config=params.llm_config,
            enricher_config=params.enricher_config,
        )
        add_log(f"Chunk 增强完成")
        await update_step(4, "done")
    else:
        await add_step(4, 6, "Chunk 上下文增强", "skipped")

    store_cfg = _get_store_config(kb)
    skip_qdrant = store_cfg.get("skip_qdrant", False)

    # 中断检查点 2：向量化前
    if await check_interrupted():
        return IngestionResult(document=doc, chunks=chunks, indexing_results=[])

    # 标记所有 chunks 为 indexing 状态
    for chunk in chunks:
        chunk.indexing_status = "indexing"
    await session.flush()

    # 批量写入向量库（异步，带错误处理）
    # 父子分块模式下：只对子块向量化，父块只存 DB 作为上下文
    await add_step(5, 6, "写入向量库", "running")
    indexing_error = None
    if not skip_qdrant:
        # 构建 ACL metadata（从文档继承）
        acl_metadata = build_acl_metadata_for_chunk(
            document_id=doc.id,
            sensitivity_level=getattr(doc, "sensitivity_level", "internal"),
            allow_users=getattr(doc, "acl_allow_users", None),
            allow_roles=getattr(doc, "acl_allow_roles", None),
            allow_groups=getattr(doc, "acl_allow_groups", None),
        )
        
        chunk_data = [
            {
                "chunk_id": chunk.id,
                "knowledge_base_id": kb.id,
                "text": chunk.text,
                "metadata": {
                    "document_id": doc.id,
                    "title": doc.title,
                    "source": params.source,
                } | (chunk.extra_metadata or {}) | acl_metadata,
            }
            for chunk in chunks
            # 父块（有 parent_id 但没有 child 标记）不写入向量库
            if not _is_parent_chunk(chunk.extra_metadata or {})
        ]
        try:
            add_log(f"向量化并写入 {len(chunk_data)} 个 chunks 到 Qdrant...")
            await vector_store.upsert_chunks(
                tenant_id=tenant_id, 
                chunks=chunk_data,
                embedding_config=embedding_config,
            )
            add_log(f"向量库写入成功")
        except Exception as e:
            indexing_error = str(e)
            add_log(f"向量库写入失败: {e}", "ERROR")
    
    # 写入 BM25 索引（同步，内存操作）
    # 同样只索引子块，父块不参与 BM25 检索
    bm25_chunks = [
        {
            "chunk_id": chunk.id,
            "text": chunk.text,
            "metadata": {
                "document_id": doc.id,
                "title": doc.title,
                "source": params.source,
            }
            | (chunk.extra_metadata or {}),
        }
        for chunk in chunks
        if not _is_parent_chunk(chunk.extra_metadata or {})
    ]
    await bm25_store.upsert_chunks(
        tenant_id=tenant_id,
        knowledge_base_id=kb.id,
        chunks=bm25_chunks,
    )

    # 收集写入结果
    indexing_results: list[IndexingResult] = []
    
    # Qdrant 写入结果（计数使用实际索引的 chunk 数量，不含父块）
    indexed_count = len(chunk_data) if not skip_qdrant else 0
    if not skip_qdrant:
        if indexing_error:
            indexing_results.append(IndexingResult(
                store_type="qdrant", success=False, chunks_count=0, error=indexing_error
            ))
        else:
            indexing_results.append(IndexingResult(
                store_type="qdrant", success=True, chunks_count=indexed_count
            ))
    
    # 更新索引状态
    for chunk in chunks:
        if indexing_error:
            chunk.indexing_status = "failed"
            chunk.indexing_error = indexing_error
            chunk.indexing_retry_count += 1
        else:
            chunk.indexing_status = "indexed"
            chunk.indexing_error = None

    # 多后端写入（Milvus/ES），返回结构化结果
    extra_result = _maybe_upsert_llamaindex(store_config=store_cfg, kb=kb, tenant_id=tenant_id, chunks=chunks)
    if extra_result is not None:
        indexing_results.append(extra_result)
        # 如果多后端写入失败，记录警告但不影响主流程
        if not extra_result.success:
            logger.warning(f"[{extra_result.store_type}] 写入失败: {extra_result.error}")

    # 失效 BM25 缓存（文档更新后需要重新加载）
    cache = get_bm25_cache()
    await cache.invalidate(tenant_id=tenant_id, kb_id=kb.id)

    # 更新步骤 5 状态
    if indexing_error:
        await update_step(5, "error")
    else:
        await update_step(5, "done")

    # 中断检查点 3：RAPTOR 索引构建前
    if await check_interrupted():
        return IngestionResult(document=doc, chunks=chunks, indexing_results=indexing_results)

    # RAPTOR 索引构建（可选，根据 KB 配置）
    raptor_config = _get_raptor_config(kb)
    if raptor_config and raptor_config.get("enabled", False):
        await add_step(6, 6, "构建 RAPTOR 索引", "running")
        add_log(f"这一步可能较慢，涉及向量化和 LLM 摘要...")
        raptor_result = await _build_raptor_index(
            session=session,
            tenant_id=tenant_id,
            kb=kb,
            chunks=chunks,
            raptor_config=raptor_config,
            embedding_config=embedding_config,
        )
        if raptor_result:
            indexing_results.append(raptor_result)
            if raptor_result.success:
                add_log(f"RAPTOR 索引构建成功")
                await update_step(6, "done")
            else:
                add_log(f"RAPTOR 索引构建失败: {raptor_result.error}", "WARNING")
                await update_step(6, "error")
    else:
        await add_step(6, 6, "构建 RAPTOR 索引", "skipped")

    total_time = time.time() - ingest_start
    add_log(f"文档入库完成! 总耗时 {total_time:.2f}s, chunks={len(chunks)}")
    
    # 保存处理日志到文档
    doc.processing_log = "\n".join(log_lines)
    # 设置处理状态为完成
    doc.processing_status = "completed"
    await session.flush()
    
    return IngestionResult(document=doc, chunks=chunks, indexing_results=indexing_results)


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


def _maybe_upsert_llamaindex(
    store_config: dict, kb: KnowledgeBase, tenant_id: str, chunks: list[Chunk]
) -> IndexingResult | None:
    """
    写入 LlamaIndex 多后端存储（Milvus/ES）
    
    返回结构化的写入结果，失败时不抛异常而是返回错误信息。
    Qdrant 已通过 vector_store 写入，此函数跳过。
    """
    store_type = store_config.get("type", "qdrant").lower()
    params = store_config.get("params", {}) if isinstance(store_config.get("params"), dict) else {}
    
    # qdrant 已通过 vector_store 写入，可跳过
    if store_type == "qdrant":
        return None
    
    # 构建索引
    try:
        index = build_index_by_store(store_type, tenant_id=tenant_id, kb_id=kb.id, params=params)
    except Exception as exc:  # noqa: BLE001
        error_msg = f"构建索引失败: {exc}"
        logger.error(f"[{store_type}] {error_msg}")
        return IndexingResult(store_type=store_type, success=False, error=error_msg)
    
    # 转换为 LlamaIndex nodes（过滤父块，只索引子块）
    indexable_chunks = [
        ch for ch in chunks
        if not _is_parent_chunk(ch.extra_metadata or {})
    ]
    nodes = nodes_from_chunks(
        chunks=[
            {
                "chunk_id": ch.id,
                "text": ch.text,
                "metadata": (ch.extra_metadata or {}) | {"knowledge_base_id": kb.id, "document_id": ch.document_id},
            }
            for ch in indexable_chunks
        ]
    )
    
    # 写入节点
    try:
        index.insert_nodes(nodes)
        logger.info(f"[{store_type}] 写入成功: {len(nodes)} chunks")
        return IndexingResult(store_type=store_type, success=True, chunks_count=len(nodes))
    except Exception as exc:  # noqa: BLE001
        error_msg = f"写入失败: {exc}"
        logger.error(f"[{store_type}] {error_msg}")
        return IndexingResult(store_type=store_type, success=False, chunks_count=0, error=error_msg)


async def _generate_document_summary(
    doc: Document,
    content: str,
    summary_config: SummaryConfig | None = None,
) -> None:
    """
    生成文档摘要（异步）
    
    生成成功后更新 doc.summary 和 doc.summary_status
    失败时设置 summary_status = "failed"
    文档太短时设置 summary_status = "skipped"
    """
    try:
        doc.summary_status = "generating"
        
        summary = await generate_summary(content, config=summary_config)
        
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


def _get_raptor_config(kb: KnowledgeBase) -> dict | None:
    """
    获取知识库的 RAPTOR 配置
    
    支持两种配置方式：
    1. kb.config.raptor.enabled = true（直接配置）
    2. kb.config.ingestion.indexer.name = 'raptor'（通过 Ground 前端配置）
    
    Args:
        kb: 知识库对象
        
    Returns:
        RAPTOR 配置字典，如果未配置则返回 None
    """
    cfg = kb.config or {}
    if not isinstance(cfg, dict):
        return None
    
    # 方式1：直接配置 raptor
    raptor_cfg = cfg.get("raptor")
    if raptor_cfg and isinstance(raptor_cfg, dict):
        return raptor_cfg
    
    # 方式2：通过 ingestion.indexer 配置
    ingestion = cfg.get("ingestion")
    if ingestion and isinstance(ingestion, dict):
        indexer = ingestion.get("indexer")
        if indexer and isinstance(indexer, dict):
            if indexer.get("name") == "raptor":
                # 将 indexer params 转换为 raptor config 格式
                params = indexer.get("params", {})
                return {
                    "enabled": True,
                    "max_layers": params.get("max_levels", 3),
                    "retrieval_mode": params.get("retrieval_mode", "collapsed"),
                    "max_clusters": params.get("max_clusters", 10),
                }
    
    return None


async def _build_raptor_index(
    session: AsyncSession,
    tenant_id: str,
    kb: KnowledgeBase,
    chunks: list[Chunk],
    raptor_config: dict,
    embedding_config: dict | None = None,
) -> IndexingResult | None:
    """
    构建 RAPTOR 索引（使用原生实现）
    
    原生实现参考 RAGFlow，使用 UMAP 降维 + GMM 聚类 + LLM 摘要。
    
    Args:
        session: 数据库会话
        tenant_id: 租户 ID
        kb: 知识库对象
        chunks: 已切分的 chunk 列表
        raptor_config: RAPTOR 配置
        embedding_config: 可选的 embedding 配置（来自调用方，与向量库写入保持一致）
        
    Returns:
        IndexingResult 或 None（如果 RAPTOR 不可用）
    """
    if not RAPTOR_NATIVE_AVAILABLE:
        logger.warning("RAPTOR 不可用（需要安装 umap-learn 和 scikit-learn）")
        return IndexingResult(
            store_type="raptor",
            success=False,
            error="RAPTOR 不可用，请安装 umap-learn 和 scikit-learn",
        )
    
    try:
        # 从 KB 配置中获取 llm 配置（embedding_config 优先使用调用方传入的）
        kb_cfg = kb.config or {}
        llm_config = None
        if isinstance(kb_cfg, dict):
            llm_config = kb_cfg.get("llm")
        
        # 创建原生索引器
        indexer = await create_raptor_native_indexer_from_config(
            embedding_config=embedding_config,
            llm_config=llm_config,
            raptor_config=raptor_config,
        )
        
        # 准备 chunk 数据（添加索引用于映射）
        chunk_data = []
        chunk_id_mapping = {}
        for idx, chunk in enumerate(chunks):
            # 只使用子块（非父块）构建 RAPTOR 索引
            if _is_parent_chunk(chunk.extra_metadata or {}):
                continue
            
            chunk_data.append({
                "text": chunk.text,
                "metadata": {
                    "chunk_idx": idx,
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    **(chunk.extra_metadata or {}),
                },
            })
            chunk_id_mapping[str(idx)] = chunk.id
        
        if not chunk_data:
            logger.warning("没有可用的 chunks 构建 RAPTOR 索引")
            return IndexingResult(
                store_type="raptor",
                success=False,
                error="没有可用的 chunks",
            )
        
        logger.info(f"[RAPTOR-Native] 开始构建索引: kb={kb.id}, chunks={len(chunk_data)}")
        
        # 构建索引（异步）
        result = await indexer.build(chunk_data)
        
        if result.total_nodes == 0:
            logger.warning("[RAPTOR-Native] 构建结果为空")
            return IndexingResult(
                store_type="raptor",
                success=False,
                error="RAPTOR 索引构建结果为空",
            )
        
        # 保存向量到向量库
        vector_count = await indexer.save_to_vector_store(
            tenant_id=tenant_id,
            knowledge_base_id=kb.id,
        )
        
        # 保存节点到数据库
        saved_count = await indexer.save_to_db(
            session=session,
            tenant_id=tenant_id,
            knowledge_base_id=kb.id,
            chunk_id_mapping=chunk_id_mapping,
        )
        
        logger.info(
            f"[RAPTOR-Native] 索引构建完成: kb={kb.id}, "
            f"总节点={result.total_nodes}, 层数={result.levels}, "
            f"叶子节点={result.leaf_nodes}, 摘要节点={result.summary_nodes}, "
            f"保存向量={vector_count}, 保存DB={saved_count}"
        )
        
        return IndexingResult(
            store_type="raptor",
            success=True,
            chunks_count=result.total_nodes,
        )
        
    except Exception as e:
        error_msg = f"RAPTOR 索引构建失败: {e}"
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return IndexingResult(
            store_type="raptor",
            success=False,
            error=error_msg,
        )


async def _enrich_chunks(
    chunks: list[Chunk],
    doc: Document,
    llm_config: dict | None = None,
    enricher_config: dict | None = None,
) -> None:
    """
    批量增强 chunks（异步）
    
    遍历 chunks，调用 ChunkEnricher 生成增强文本，
    更新 chunk.enriched_text 和 chunk.enrichment_status
    
    Args:
        chunks: 要增强的 chunk 列表
        doc: 文档对象
        llm_config: 前端传入的 LLM 配置（优先级高于环境变量）
        enricher_config: 前端传入的增强器配置（包含 name 和 params）
    """
    enricher = get_chunk_enricher(llm_config=llm_config, enricher_config=enricher_config)
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
