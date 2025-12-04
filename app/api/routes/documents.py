"""
文档管理接口

提供文档的上传（摄取）、删除等操作。
上传的文档会被切分成片段并向量化存入向量数据库。
"""

import logging

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant
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
from app.schemas.document import BatchIngestRequest, BatchIngestResponse, BatchIngestResult
from app.schemas.internal import IngestionParams
from app.services.ingestion import ensure_kb_belongs_to_tenant, ingest_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/knowledge-bases/{kb_id}/documents", response_model=DocumentIngestResponse)
async def ingest_document_endpoint(
    payload: DocumentIngestRequest,
    kb_id: str = Path(..., description="Knowledge base ID"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
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
    
    # 执行文档摄取（切分、向量化、存储）
    result = await ingest_document(
        db,
        tenant_id=tenant.id,
        kb=kb,
        params=params,
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
        created_at=doc.created_at,
        summary=doc.summary,
        summary_status=doc.summary_status,
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


@router.delete("/v1/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str = Path(..., description="Document ID"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
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
        bm25_store.delete_by_ids(
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
    file: UploadFile = File(..., description="要上传的文本文件"),
    title: str | None = Form(default=None, description="文档标题（可选，默认使用文件名）"),
    source: str | None = Form(default=None, description="来源类型"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    文件直传上传文档（multipart/form-data）
    
    支持的文件类型：.txt, .md, .markdown, .json
    文件大小限制：10MB
    """
    # 验证知识库归属
    kb = await ensure_kb_belongs_to_tenant(db, kb_id=kb_id, tenant_id=tenant.id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    # 验证文件类型
    allowed_extensions = {".txt", ".md", ".markdown", ".json"}
    filename = file.filename or "untitled.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "detail": f"不支持的文件类型: {ext}，仅支持 {allowed_extensions}"},
        )

    # 读取文件内容
    try:
        content_bytes = await file.read()
        # 限制文件大小 10MB
        if len(content_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "VALIDATION_ERROR", "detail": "文件大小超过 10MB 限制"},
            )
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "detail": "文件编码错误，仅支持 UTF-8"},
        )

    # 使用文件名作为默认标题
    doc_title = title or filename.rsplit(".", 1)[0]
    doc_source = source or f"file:{ext.lstrip('.')}"

    # 构建摄取参数对象
    params = IngestionParams(
        title=doc_title,
        content=content,
        metadata={"original_filename": filename},
        source=doc_source,
    )
    
    # 执行文档摄取
    result = await ingest_document(
        db,
        tenant_id=tenant.id,
        kb=kb,
        params=params,
    )
    await db.commit()
    
    # 记录多后端写入失败
    for failed in result.failed_stores():
        logger.warning(f"文档 {result.document.id} 多后端写入失败: [{failed.store_type}] {failed.error}")

    logger.info(f"Uploaded file '{filename}' as document {result.document.id} with {len(result.chunks)} chunks")
    return DocumentIngestResponse(document_id=result.document.id, chunk_count=len(result.chunks))


@router.post("/v1/knowledge-bases/{kb_id}/documents/batch", response_model=BatchIngestResponse)
async def batch_ingest_endpoint(
    payload: BatchIngestRequest,
    kb_id: str = Path(..., description="Knowledge base ID"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
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
