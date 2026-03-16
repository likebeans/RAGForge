"""
文档管理接口

提供文档的上传（摄取）、删除等操作。
上传的文档会被切分成片段并向量化存入向量数据库。
"""

import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant, require_role
from app.auth.api_key import APIKeyContext
from app.infra.bm25_store import bm25_store
from app.infra.vector_store import vector_store
from app.models import Chunk, Document, KnowledgeBase
from app.schemas import (
    ChunkListResponse,
    ChunkResponse,
    DocumentDetailResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.schemas.document import (
    AdvancedBatchIngestRequest,
    BatchIngestRequest,
    BatchIngestResponse,
    BatchIngestResult,
)
from app.schemas.internal import IngestionParams
from app.services.ingestion import ensure_kb_belongs_to_tenant, ingest_document
from app.services.model_config import model_config_resolver
from app.pipeline import operator_registry
from app.config import get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/knowledge-bases/{kb_id}/documents", response_model=DocumentIngestResponse)
async def ingest_document_endpoint(
    payload: DocumentIngestRequest,
    kb_id: str = Path(..., description="Knowledge base ID"),
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    上传文档到知识库
    
    处理流程：
    1. 验证知识库是否属于当前租户
    2. 解析文档内容
    3. 切分成文本片段
    4. 向量化并存入向量数据库
    """
    # 验证知识库归属
    kb = await ensure_kb_belongs_to_tenant(db, kb_id=kb_id, tenant_id=tenant.id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    content = payload.content
    # 从 URL 拉取内容（可选）
    if not content and payload.source_url:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(payload.source_url)
                resp.raise_for_status()
                content = resp.text
        except Exception as exc:  # pragma: no cover - 网络异常
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "FETCH_FAILED", "detail": f"拉取内容失败: {exc}"},
            )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "detail": "content 不能为空"},
        )

    # 构建摄取参数对象
    params = IngestionParams(
        title=payload.title,
        content=content,
        metadata=payload.metadata,
        source=payload.source or ("url" if payload.source_url else payload.source),
        # ACL 字段
        sensitivity_level=payload.sensitivity_level,
        acl_users=payload.acl_users,
        acl_roles=payload.acl_roles,
        acl_groups=payload.acl_groups,
    )
    
    # 使用 ModelConfigResolver 获取 Embedding 配置
    # 文档入库时，优先使用 KB 配置的 embedding（保持向量维度一致），其次租户默认
    embedding_config = None
    try:
        embed_config = await model_config_resolver.get_embedding_config(
            session=db, 
            kb=kb, 
            tenant=tenant,
        )
        logger.info(f"[DEBUG] embed_config={embed_config}")
        if embed_config.get("embedding_provider"):
            # 构建带有租户 API Key 的 provider 配置
            provider_config = model_config_resolver.build_provider_config(
                embed_config, "embedding", tenant=tenant
            )
            logger.info(f"[DEBUG] provider_config={provider_config}")
            embedding_config = {
                "provider": provider_config.get("provider"),
                "model": provider_config.get("model"),
                "api_key": provider_config.get("api_key"),
                "base_url": provider_config.get("base_url"),
                "dim": embed_config.get("embedding_dim"),
            }
            logger.info(f"文档入库使用 Embedding 配置: {embedding_config.get('provider')}/{embedding_config.get('model')} (dim={embedding_config.get('dim')})")
        else:
            logger.warning("[DEBUG] embed_config 中无 embedding_provider，将回退到环境变量")
    except Exception as e:
        logger.warning(f"获取 Embedding 配置失败，将回退到知识库配置: {type(e).__name__}: {e}")
    
    # 执行文档摄取（切分、向量化、存储）
    result = await ingest_document(
        db,
        tenant_id=tenant.id,
        kb=kb,
        params=params,
        embedding_config=embedding_config,
    )
    await db.commit()
    
    # 记录多后端写入失败（不阻塞响应）
    for failed in result.failed_stores():
        logger.warning(f"文档 {result.document.id} 多后端写入失败: [{failed.store_type}] {failed.error}")

    return DocumentIngestResponse(document_id=result.document.id, chunk_count=len(result.chunks))


@router.get("/v1/knowledge-bases/{kb_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    kb_id: str = Path(..., description="Knowledge base ID"),
    page: int = Query(1, ge=1, description="页码（>=1）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（1-100）"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    列出知识库下的所有文档
    """
    # 验证知识库归属
    kb = await ensure_kb_belongs_to_tenant(db, kb_id=kb_id, tenant_id=tenant.id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    total_result = await db.execute(
        select(func.count()).select_from(
            select(Document.id)
            .where(Document.knowledge_base_id == kb_id)
            .subquery()
        )
    )
    total = total_result.scalar_one()

    # 查询文档列表，带 chunk 数量
    result = await db.execute(
        select(
            Document,
            func.count(Chunk.id).label("chunk_count"),
        )
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(Document.knowledge_base_id == kb_id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = result.all()

    items = []
    for doc, chunk_count in rows:
        items.append(
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                knowledge_base_id=doc.knowledge_base_id,
                metadata=doc.extra_metadata,
                source=doc.source,
                chunk_count=chunk_count,
                processing_status=doc.processing_status,
                created_at=doc.created_at,
            )
        )

    pages = (total + page_size - 1) // page_size if total is not None else 0
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/v1/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: str = Path(..., description="Document ID"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取文档详情（包含摘要状态和 chunk 计数）
    """
    result = await db.execute(
        select(
            Document,
            KnowledgeBase,
            func.count(Chunk.id).label("chunk_count"),
        )
        .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(
            Document.id == doc_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
        .group_by(Document.id, KnowledgeBase.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOC_NOT_FOUND", "detail": "Document not found"},
        )

    doc, _, chunk_count = row
    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        knowledge_base_id=doc.knowledge_base_id,
        metadata=doc.extra_metadata,
        source=doc.source,
        chunk_count=chunk_count,
        processing_status=doc.processing_status,
        created_at=doc.created_at,
        summary=doc.summary,
        summary_status=doc.summary_status,
        processing_log=doc.processing_log,
    )


@router.get("/v1/documents/{doc_id}/chunks", response_model=ChunkListResponse)
async def list_document_chunks(
    doc_id: str = Path(..., description="Document ID"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    列出文档的 Chunk 列表，包含索引状态和元数据
    """
    # 验证文档归属租户
    doc_result = await db.execute(
        select(Document, KnowledgeBase)
        .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .where(
            Document.id == doc_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    doc_row = doc_result.first()
    if not doc_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOC_NOT_FOUND", "detail": "Document not found"},
        )

    chunks_result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == doc_id)
        .where(Chunk.tenant_id == tenant.id)
        .order_by(Chunk.created_at.asc())
    )
    chunks = chunks_result.scalars().all()

    def _chunk_index(ch: Chunk) -> int:
        meta = ch.extra_metadata or {}
        try:
            return int(meta.get("chunk_index", 0))
        except Exception:
            return 0

    items = [
        ChunkResponse(
            id=ch.id,
            document_id=ch.document_id,
            index=_chunk_index(ch) if ch.extra_metadata else idx,
            text=ch.text,
            indexing_status=ch.indexing_status,
            metadata=ch.extra_metadata or {},
        )
        for idx, ch in enumerate(sorted(chunks, key=_chunk_index))
    ]
    return ChunkListResponse(items=items, total=len(items))


@router.post("/v1/documents/{doc_id}/interrupt", status_code=status.HTTP_200_OK)
async def interrupt_document_processing(
    doc_id: str = Path(..., description="Document ID"),
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    中断文档入库处理
    
    将文档的 processing_status 设置为 interrupted，
    入库流程会在下一个检查点检测到中断状态并停止处理。
    """
    # 查询文档及其知识库
    result = await db.execute(
        select(Document, KnowledgeBase)
        .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .where(
            Document.id == doc_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOC_NOT_FOUND", "detail": "Document not found"},
        )

    doc, _ = row
    
    # 只能中断处理中的文档
    if doc.processing_status not in ("pending", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATUS",
                "detail": f"文档当前状态为 {doc.processing_status}，无法中断",
            },
        )
    
    # 设置中断状态
    doc.processing_status = "interrupted"
    # 追加中断日志
    import datetime
    interrupt_log = f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] [WARN] 用户请求中断处理"
    if doc.processing_log:
        doc.processing_log += interrupt_log
    else:
        doc.processing_log = interrupt_log.strip()
    
    await db.commit()
    
    logger.info(f"Document {doc_id} processing interrupted by user")
    return {"status": "interrupted", "document_id": doc_id}


@router.delete("/v1/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str = Path(..., description="Document ID"),
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除文档及其所有 Chunks 和向量

    处理流程：
    1. 验证文档存在且属于当前租户
    2. 删除向量数据库中的向量
    3. 删除数据库中的 Chunks
    4. 删除数据库中的 Document
    """
    # 查询文档及其知识库
    result = await db.execute(
        select(Document, KnowledgeBase)
        .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .where(
            Document.id == doc_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOC_NOT_FOUND", "detail": "Document not found"},
        )

    doc, kb = row

    # 获取该文档下所有 Chunk 的 ID
    chunk_result = await db.execute(
        select(Chunk.id).where(Chunk.document_id == doc_id)
    )
    chunk_ids = [row[0] for row in chunk_result.fetchall()]

    # 删除向量数据库中的向量
    if chunk_ids:
        try:
            await vector_store.delete_by_ids(tenant.id, chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} vectors for document {doc_id}")
        except Exception as e:
            logger.warning(f"Failed to delete vectors for document {doc_id}: {e}")
        await bm25_store.delete_by_ids(
            tenant_id=tenant.id,
            knowledge_base_id=doc.knowledge_base_id,
            chunk_ids=chunk_ids,
        )

    # 删除 Chunks
    await db.execute(delete(Chunk).where(Chunk.document_id == doc_id))

    # 删除 Document
    await db.delete(doc)
    await db.commit()

    logger.info(f"Deleted document {doc_id} with {len(chunk_ids)} chunks")


@router.post("/v1/knowledge-bases/{kb_id}/documents/upload", response_model=DocumentIngestResponse)
async def upload_file_endpoint(
    kb_id: str = Path(..., description="Knowledge base ID"),
    file: UploadFile = File(..., description="要上传的文件"),
    title: str | None = Form(default=None, description="文档标题（可选，默认使用文件名）"),
    source: str | None = Form(default=None, description="来源类型"),
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    文件直传上传文档（multipart/form-data）
    
    支持的文件类型：
    - 文本：.txt, .md, .markdown, .json
    - Excel：.xlsx, .xls
    - Word：.docx
    - PDF：.pdf（需要 MinerU 服务）
    
    文件大小限制：50MB
    """
    from app.pipeline.parsers import parser_registry
    
    # 验证知识库归属
    kb = await ensure_kb_belongs_to_tenant(db, kb_id=kb_id, tenant_id=tenant.id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    # 验证文件类型
    filename = file.filename or "untitled.txt"
    if not parser_registry.can_parse(filename):
        supported = ", ".join(sorted(parser_registry.supported_extensions()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "detail": f"不支持的文件类型，支持: {supported}"},
        )

    # 读取文件内容
    content_bytes = await file.read()
    
    # 限制文件大小 50MB
    max_size_mb = 50
    if len(content_bytes) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "detail": f"文件大小超过 {max_size_mb}MB 限制"},
        )

    # 使用解析器解析文件
    try:
        parse_result = await parser_registry.parse(content_bytes, filename)
        content = parse_result.content
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PARSE_ERROR", "detail": str(e)},
        )
    except Exception as e:
        logger.error(f"文件解析失败: {filename}, {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PARSE_ERROR", "detail": f"文件解析失败: {type(e).__name__}"},
        )

    # 使用文件名作为默认标题
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    doc_title = title or filename.rsplit(".", 1)[0]
    doc_source = source or f"file:{ext.lstrip('.')}"

    # 构建摄取参数对象，包含解析元数据
    doc_metadata = {"original_filename": filename}
    doc_metadata.update(parse_result.metadata)
    
    # 从 KB 配置读取入库选项
    kb_cfg = kb.config or {}
    ingestion_cfg = kb_cfg.get("ingestion", {}) if isinstance(kb_cfg, dict) else {}
    enricher_cfg = ingestion_cfg.get("enricher", {}) if isinstance(ingestion_cfg, dict) else {}
    indexer_cfg = ingestion_cfg.get("indexer", {}) if isinstance(ingestion_cfg, dict) else {}
    
    # enrich_chunks 可能在 ingestion 或 ingestion.enricher 中
    enrich_chunks = (
        ingestion_cfg.get("enrich_chunks", False) or 
        enricher_cfg.get("enrich_chunks", False)
    )
    # generate_summary 可能在 ingestion 或 ingestion.enricher 中
    generate_summary = ingestion_cfg.get("generate_summary", enricher_cfg.get("generate_summary", True))
    
    # 如果启用了增强，获取租户的 LLM 配置
    llm_config = None
    if enrich_chunks or generate_summary:
        try:
            llm_merged = await model_config_resolver.get_llm_config(
                session=db, tenant=tenant
            )
            llm_config = model_config_resolver.build_provider_config(
                llm_merged, "llm", tenant=tenant
            )
            logger.info(f"[Enrichment] 使用 LLM 配置: provider={llm_config.get('provider')}, model={llm_config.get('model')}")
        except Exception as e:
            logger.warning(f"获取 LLM 配置失败: {e}")
    
    # 使用 ModelConfigResolver 获取 Embedding 配置
    embedding_config = None
    try:
        embed_config = await model_config_resolver.get_embedding_config(
            session=db, kb=kb, tenant=tenant
        )
        if embed_config.get("embedding_provider"):
            provider_config = model_config_resolver.build_provider_config(
                embed_config, "embedding", tenant=tenant
            )
            embedding_config = {
                "provider": provider_config.get("provider"),
                "model": provider_config.get("model"),
                "api_key": provider_config.get("api_key"),
                "base_url": provider_config.get("base_url"),
                "dim": embed_config.get("embedding_dim"),
            }
    except ValueError:
        pass  # 回退到知识库/环境变量配置
    
    # 【异步模式】先创建 Document 记录（状态为 processing），立即返回
    new_doc = Document(
        tenant_id=tenant.id,
        knowledge_base_id=kb_id,
        title=doc_title,
        source=doc_source,
        raw_content=content,
        extra_metadata=doc_metadata,
        processing_status="processing",
        summary_status="pending",
        processing_log="[等待处理] 文档已创建，正在排队入库...\n",
    )
    db.add(new_doc)
    await db.flush()
    doc_id = new_doc.id
    
    await db.commit()
    
    logger.info(f"文件上传成功，文档 {doc_id} 已创建，开始后台入库")
    
    # 启动后台任务执行实际入库
    asyncio.create_task(
        _background_file_ingest(
            tenant_id=tenant.id,
            kb_id=kb_id,
            doc_id=doc_id,
            content=content,
            doc_title=doc_title,
            doc_metadata=doc_metadata,
            doc_source=doc_source,
            filename=filename,
            content_bytes=content_bytes,
            generate_summary=generate_summary,
            enrich_chunks=enrich_chunks,
            llm_config=llm_config,
            enricher_cfg=enricher_cfg,
            indexer_cfg=indexer_cfg,
            embedding_config=embedding_config,
        )
    )
    
    # 立即返回（chunk_count 暂为 0，后台任务完成后更新）
    return DocumentIngestResponse(document_id=doc_id, chunk_count=0)


@router.post("/v1/knowledge-bases/{kb_id}/documents/batch", response_model=BatchIngestResponse)
async def batch_ingest_endpoint(
    payload: BatchIngestRequest,
    kb_id: str = Path(..., description="Knowledge base ID"),
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    批量上传文档（最多 50 个）
    
    所有文档在同一事务中处理，部分失败不会回滚已成功的文档。
    """
    # 验证知识库归属
    kb = await ensure_kb_belongs_to_tenant(db, kb_id=kb_id, tenant_id=tenant.id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    results: list[BatchIngestResult] = []
    succeeded = 0
    failed = 0

    # 使用 ModelConfigResolver 获取 Embedding 配置（批量入库时只获取一次）
    embedding_config = None
    try:
        embed_config = await model_config_resolver.get_embedding_config(
            session=db, kb=kb, tenant=tenant
        )
        if embed_config.get("embedding_provider"):
            provider_config = model_config_resolver.build_provider_config(
                embed_config, "embedding", tenant=tenant
            )
            embedding_config = {
                "provider": provider_config.get("provider"),
                "model": provider_config.get("model"),
                "api_key": provider_config.get("api_key"),
                "base_url": provider_config.get("base_url"),
                "dim": embed_config.get("embedding_dim"),
            }
    except ValueError:
        pass  # 回退到知识库/环境变量配置

    for item in payload.documents:
        try:
            params = IngestionParams(
                title=item.title,
                content=item.content,
                metadata=item.metadata,
                source=item.source,
            )
            result = await ingest_document(
                db,
                tenant_id=tenant.id,
                kb=kb,
                params=params,
                embedding_config=embedding_config,
            )
            await db.commit()
            
            # 记录多后端写入失败
            for failed_store in result.failed_stores():
                logger.warning(f"文档 {result.document.id} 多后端写入失败: [{failed_store.store_type}] {failed_store.error}")
            
            results.append(BatchIngestResult(
                title=item.title,
                document_id=result.document.id,
                chunk_count=len(result.chunks),
                success=True,
            ))
            succeeded += 1
        except Exception as e:
            logger.warning(f"Failed to ingest document '{item.title}': {e}")
            await db.rollback()
            results.append(BatchIngestResult(
                title=item.title,
                success=False,
                error=str(e),
            ))
            failed += 1

    logger.info(f"Batch ingest completed: {succeeded} succeeded, {failed} failed")
    return BatchIngestResponse(
        results=results,
        total=len(payload.documents),
        succeeded=succeeded,
        failed=failed,
    )


@router.post("/v1/knowledge-bases/{kb_id}/documents/advanced-batch", response_model=BatchIngestResponse)
async def advanced_batch_ingest_endpoint(
    payload: AdvancedBatchIngestRequest,
    kb_id: str = Path(..., description="Knowledge base ID"),
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    高级批量上传文档（支持自定义配置）
    
    支持覆盖以下配置：
    - chunker: 切分器名称和参数
    - generate_summary: 是否生成文档摘要
    - enrich_chunks: 是否进行 Chunk 增强
    - embedding_provider/model: Embedding 模型配置
    
    所有文档使用相同的配置进行处理。
    """
    # 验证知识库归属
    kb = await ensure_kb_belongs_to_tenant(db, kb_id=kb_id, tenant_id=tenant.id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    # 验证 chunker 配置
    if payload.chunker:
        chunker_name = payload.chunker.name
        if chunker_name not in operator_registry.list("chunker"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_CHUNKER",
                    "detail": f"未知 chunker: {chunker_name}，可用: {operator_registry.list('chunker')}"
                },
            )

    # 构建临时 KB 配置（覆盖原配置）
    temp_kb_config = dict(kb.config or {})
    if payload.chunker:
        if "ingestion" not in temp_kb_config:
            temp_kb_config["ingestion"] = {}
        temp_kb_config["ingestion"]["chunker"] = {
            "name": payload.chunker.name,
            "params": payload.chunker.params or {},
        }
    
    if payload.embedding_provider and payload.embedding_model:
        temp_kb_config["embedding"] = {
            "provider": payload.embedding_provider,
            "model": payload.embedding_model,
        }
    
    # 临时更新 KB 配置用于入库
    original_config = kb.config
    kb.config = temp_kb_config
    
    # 构建 embedding 配置（优先使用 API 传入的配置，其次租户配置）
    embedding_config: dict | None = None
    if payload.embedding_provider and payload.embedding_model:
        settings = get_settings()
        try:
            embedding_config = settings._get_provider_config(
                payload.embedding_provider,
                payload.embedding_model
            )
            logger.info(f"Advanced batch 使用 API 传入的 embedding 配置: {payload.embedding_provider}/{payload.embedding_model}")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_EMBEDDING_CONFIG", "detail": str(e)}
            )
    else:
        # 回退到租户配置
        try:
            embed_config = await model_config_resolver.get_embedding_config(
                session=db, kb=kb, tenant=tenant
            )
            if embed_config.get("embedding_provider"):
                provider_config = model_config_resolver.build_provider_config(
                    embed_config, "embedding", tenant=tenant
                )
                embedding_config = {
                    "provider": provider_config.get("provider"),
                    "model": provider_config.get("model"),
                    "api_key": provider_config.get("api_key"),
                    "base_url": provider_config.get("base_url"),
                    "dim": embed_config.get("embedding_dim"),
                }
        except ValueError:
            pass  # 回退到知识库/环境变量配置

    results: list[BatchIngestResult] = []
    succeeded = 0
    failed = 0

    try:
        for item in payload.documents:
            try:
                params = IngestionParams(
                    title=item.title,
                    content=item.content,
                    metadata=item.metadata,
                    source=item.source,
                    generate_doc_summary=payload.generate_summary,
                    enrich_chunks=payload.enrich_chunks,
                )
                result = await ingest_document(
                    db,
                    tenant_id=tenant.id,
                    kb=kb,
                    params=params,
                    embedding_config=embedding_config,
                )
                await db.commit()
                
                # 记录多后端写入失败
                for failed_store in result.failed_stores():
                    logger.warning(f"文档 {result.document.id} 多后端写入失败: [{failed_store.store_type}] {failed_store.error}")
                
                results.append(BatchIngestResult(
                    title=item.title,
                    document_id=result.document.id,
                    chunk_count=len(result.chunks),
                    success=True,
                ))
                succeeded += 1
            except Exception as e:
                logger.warning(f"Failed to ingest document '{item.title}': {e}")
                await db.rollback()
                results.append(BatchIngestResult(
                    title=item.title,
                    success=False,
                    error=str(e),
                ))
                failed += 1
    finally:
        # 恢复原配置
        kb.config = original_config

    logger.info(f"Advanced batch ingest completed: {succeeded} succeeded, {failed} failed")
    return BatchIngestResponse(
        results=results,
        total=len(payload.documents),
        succeeded=succeeded,
        failed=failed,
    )


async def _background_file_ingest(
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    content: str,
    doc_title: str,
    doc_metadata: dict,
    doc_source: str,
    filename: str,
    content_bytes: bytes,
    generate_summary: bool,
    enrich_chunks: bool,
    llm_config: dict | None,
    enricher_cfg: dict | None,
    indexer_cfg: dict | None,
    embedding_config: dict | None,
):
    """
    后台任务：执行实际的文档入库（chunking、embedding、写入向量库）
    
    此函数在独立的数据库会话中运行，不影响主请求的响应速度。
    """
    from datetime import datetime
    
    # 让出控制权，确保任务在正确的事件循环上下文中运行
    await asyncio.sleep(0)
    
    logger.info(f"[后台入库] 开始处理文档 {doc_id}: {doc_title}")
    
    async with SessionLocal() as db:
        try:
            # 获取知识库
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if not kb:
                logger.error(f"[后台入库] 知识库 {kb_id} 不存在")
                return
            
            # 获取文档记录
            doc_result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = doc_result.scalar_one_or_none()
            if not doc:
                logger.error(f"[后台入库] 文档 {doc_id} 不存在")
                return
            
            # 更新处理日志
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            doc.processing_log = f"[{ts}] [INFO] 开始处理文档: {doc_title}\n"
            await db.flush()
            
            # 构建 IngestionParams
            params = IngestionParams(
                title=doc_title,
                content=content,
                metadata=doc_metadata,
                source=doc_source,
                generate_doc_summary=generate_summary,
                enrich_chunks=enrich_chunks,
                llm_config=llm_config,
                enricher_config=enricher_cfg,
                indexer_config=indexer_cfg,
                existing_doc_id=doc_id,  # 使用已存在的文档 ID
            )
            
            # 执行入库
            result = await ingest_document(
                db,
                tenant_id=tenant_id,
                kb=kb,
                params=params,
                embedding_config=embedding_config,
            )
            
            # 存储原始文件到 OSS
            from app.services.file_storage import get_file_storage
            file_storage = get_file_storage()
            if file_storage.enabled:
                try:
                    raw_file_path = await file_storage.store_raw_file(
                        tenant_id=tenant_id,
                        doc_id=doc_id,
                        filename=filename,
                        content=content_bytes,
                    )
                    if raw_file_path:
                        doc.raw_file_path = raw_file_path
                        logger.info(f"[后台入库] 原始文件已存储到 OSS: {raw_file_path}")
                except Exception as e:
                    logger.warning(f"[后台入库] 原始文件存储失败（不影响入库）: {e}")
            
            # 更新文档状态为完成
            doc.processing_status = "completed"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            doc.processing_log += f"[{ts}] [INFO] 入库完成，共 {len(result.chunks)} 个 chunks\n"
            
            await db.commit()
            
            # 记录多后端写入失败
            for failed_store in result.failed_stores():
                logger.warning(f"[后台入库] 文档 {doc_id} 多后端写入失败: [{failed_store.store_type}] {failed_store.error}")
            
            logger.info(f"[后台入库] 文档 {doc_id} 入库完成，共 {len(result.chunks)} 个 chunks")
            
        except Exception as e:
            logger.error(f"[后台入库] 文档 {doc_id} 入库失败: {type(e).__name__}: {e}")
            try:
                # 更新文档状态为失败
                doc_result = await db.execute(
                    select(Document).where(Document.id == doc_id)
                )
                doc = doc_result.scalar_one_or_none()
                if doc:
                    doc.processing_status = "failed"
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    doc.processing_log += f"[{ts}] [ERROR] 入库失败: {type(e).__name__}: {e}\n"
                    await db.commit()
            except Exception as inner_e:
                logger.error(f"[后台入库] 更新文档状态失败: {inner_e}")
