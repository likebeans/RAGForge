"""
Ground (Playground 临时知识库) API

Ground 会创建一个临时知识库，用于实验流程，支持保存为正式知识库或删除。
"""

import asyncio
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant, require_role
from app.auth.api_key import APIKeyContext
from app.models import KnowledgeBase, Document, Chunk
from app.infra.vector_store import vector_store
from app.infra.bm25_store import bm25_store
from app.db.session import SessionLocal
from app.schemas.ground import GroundCreate, GroundInfo, GroundListResponse

router = APIRouter(prefix="/v1/grounds", tags=["grounds"])


def _is_ground(kb: KnowledgeBase) -> bool:
    cfg = kb.config or {}
    return bool(cfg.get("is_ground") and cfg.get("ground_id"))


def _build_ground_info(kb: KnowledgeBase, doc_count: int) -> GroundInfo:
    cfg = kb.config or {}
    return GroundInfo(
        ground_id=cfg.get("ground_id") or kb.id,
        knowledge_base_id=kb.id,
        name=kb.name,
        description=kb.description,
        created_at=kb.created_at,
        document_count=doc_count,
        saved=not cfg.get("is_ground"),
    )


@router.post("/", response_model=GroundInfo)
@router.post("", response_model=GroundInfo)
async def create_ground(
    payload: GroundCreate,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    name = payload.name or f"ground-{str(uuid4())[:8]}"
    ground_id = str(uuid4())

    cfg = {"is_ground": True, "ground_id": ground_id, "saved": False}
    kb = KnowledgeBase(
        tenant_id=tenant.id,
        name=name,
        description=payload.description,
        config=cfg,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return _build_ground_info(kb, 0)


@router.get("/", response_model=GroundListResponse)
@router.get("", response_model=GroundListResponse)
async def list_grounds(
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        ).order_by(KnowledgeBase.created_at.desc())
    )
    kbs = [kb for kb in result.scalars().all() if _is_ground(kb)]

    # 统计文档数量
    doc_counts: dict[str, int] = {}
    if kbs:
        doc_result = await db.execute(
            select(Document.knowledge_base_id, func.count())
            .where(Document.knowledge_base_id.in_([kb.id for kb in kbs]))
            .group_by(Document.knowledge_base_id)
        )
        doc_counts = {row[0]: row[1] for row in doc_result.fetchall()}

    items = [_build_ground_info(kb, doc_counts.get(kb.id, 0)) for kb in kbs]
    return GroundListResponse(items=items, total=len(items))


@router.get("/{ground_id}", response_model=GroundInfo)
async def get_ground(
    ground_id: str,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = next((kb for kb in result.scalars().all() if (kb.config or {}).get("ground_id") == ground_id), None)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GROUND_NOT_FOUND", "detail": "Ground not found"},
        )

    doc_count_result = await db.execute(
        select(func.count()).select_from(
            select(Document.id).where(Document.knowledge_base_id == kb.id).subquery()
        )
    )
    doc_count = doc_count_result.scalar_one()
    return _build_ground_info(kb, doc_count)


@router.post("/{ground_id}/save", response_model=GroundInfo)
async def save_ground_as_kb(
    ground_id: str,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = next((kb for kb in result.scalars().all() if (kb.config or {}).get("ground_id") == ground_id), None)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GROUND_NOT_FOUND", "detail": "Ground not found"},
        )

    cfg = kb.config or {}
    cfg.pop("is_ground", None)
    cfg["saved"] = True
    kb.config = cfg
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    doc_count_result = await db.execute(
        select(func.count()).select_from(
            select(Document.id).where(Document.knowledge_base_id == kb.id).subquery()
        )
    )
    doc_count = doc_count_result.scalar_one()
    return _build_ground_info(kb, doc_count)


@router.delete("/{ground_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ground(
    ground_id: str,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    # 找到 ground 对应的知识库
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = next((kb for kb in result.scalars().all() if (kb.config or {}).get("ground_id") == ground_id), None)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GROUND_NOT_FOUND", "detail": "Ground not found"},
        )

    if not (kb.config or {}).get("is_ground"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "GROUND_ALREADY_SAVED", "detail": "Ground has been saved as a knowledge base"},
        )

    # 删除向量、文档、知识库
    doc_result = await db.execute(
        select(Document.id).where(Document.knowledge_base_id == kb.id)
    )
    doc_ids = [row[0] for row in doc_result.fetchall()]

    if doc_ids:
        chunk_result = await db.execute(
            select(Chunk.id).where(Chunk.document_id.in_(doc_ids))
        )
        chunk_ids = [row[0] for row in chunk_result.fetchall()]
        if chunk_ids:
            try:
                await vector_store.delete_by_ids(tenant.id, chunk_ids)
            except Exception:
                pass
        await db.execute(delete(Document).where(Document.id.in_(doc_ids)))
        await db.execute(delete(Chunk).where(Chunk.document_id.in_(doc_ids)))

    await db.delete(kb)
    await bm25_store.delete_by_kb(tenant_id=tenant.id, knowledge_base_id=kb.id)
    await db.commit()


# ==================== 分块预览 API ====================
from pydantic import BaseModel
from app.pipeline import operator_registry


class ChunkPreviewRequest(BaseModel):
    """分块预览请求"""
    document_id: str
    chunker: str = "recursive"
    chunker_params: dict | None = None


class ChunkPreviewItem(BaseModel):
    """分块预览结果项"""
    index: int
    text: str
    char_count: int
    metadata: dict | None = None  # 切分器输出的元数据（如 parent_id, child 等）


class ChunkPreviewResponse(BaseModel):
    """分块预览响应"""
    document_id: str
    document_title: str
    chunker: str
    total_chunks: int
    chunks: list[ChunkPreviewItem]


@router.post("/{ground_id}/chunk-preview", response_model=ChunkPreviewResponse)
async def preview_document_chunks(
    ground_id: str,
    payload: ChunkPreviewRequest,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    预览指定文档的分块结果
    """
    # 获取 ground 对应的知识库
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = None
    for k in result.scalars().all():
        cfg = k.config or {}
        if cfg.get("ground_id") == ground_id:
            kb = k
            break
    
    if not kb:
        raise HTTPException(status_code=404, detail={"code": "GROUND_NOT_FOUND", "detail": "Ground not found"})
    
    # 获取文档
    doc_result = await db.execute(
        select(Document).where(
            Document.id == payload.document_id,
            Document.knowledge_base_id == kb.id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "DOCUMENT_NOT_FOUND", "detail": "Document not found"})
    
    # 从 raw_content 获取原始文件内容
    content = doc.raw_content or ""
    if not content:
        raise HTTPException(status_code=400, detail={"code": "NO_RAW_CONTENT", "detail": "Document has no raw content. Please re-upload the file."})
    
    chunker_name = payload.chunker or "recursive"
    chunker_params = payload.chunker_params or {}
    
    # 获取 chunker
    try:
        chunker_cls = operator_registry.get("chunker", chunker_name)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_CHUNKER", "detail": f"Unknown chunker: {chunker_name}"},
        )
    
    # 实例化并执行分块
    chunker = chunker_cls(**chunker_params)
    pieces = chunker.chunk(content)
    
    chunks = [
        ChunkPreviewItem(
            index=i + 1,
            text=p.text,
            char_count=len(p.text),
            metadata=p.metadata if p.metadata else None,
        )
        for i, p in enumerate(pieces)
    ]
    
    return ChunkPreviewResponse(
        document_id=payload.document_id,
        document_title=doc.title,
        chunker=chunker_name,
        total_chunks=len(chunks),
        chunks=chunks,
    )


# ==================== Ground 文档上传 API ====================
class GroundDocumentResponse(BaseModel):
    """Ground 文档上传响应"""
    id: str
    title: str
    source: str | None = None
    file_size: int


@router.post("/{ground_id}/documents/upload", response_model=GroundDocumentResponse)
async def upload_ground_document(
    ground_id: str,
    file: UploadFile = File(..., description="要上传的文本文件"),
    title: str | None = Form(default=None, description="文档标题（可选，默认使用文件名）"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    上传文件到 Ground（只保存原始内容，不做切分处理）
    
    这是 Ground/Playground 专用的上传接口：
    - 只保存文件原始内容到 raw_content 字段
    - 不执行任何切分、向量化处理
    - 后续可通过分块预览功能测试不同切分效果
    
    支持的文件类型：.txt, .md, .markdown, .json
    文件大小限制：10MB
    """
    # 获取 ground 对应的知识库
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = None
    for k in result.scalars().all():
        cfg = k.config or {}
        if cfg.get("ground_id") == ground_id:
            kb = k
            break
    
    if not kb:
        raise HTTPException(status_code=404, detail={"code": "GROUND_NOT_FOUND", "detail": "Ground not found"})
    
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
        file_size = len(content_bytes)
        # 限制文件大小 10MB
        if file_size > 10 * 1024 * 1024:
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
    doc_source = f"file:{ext.lstrip('.')}"
    
    # 创建文档记录，只保存原始内容
    doc = Document(
        id=str(uuid4()),
        tenant_id=tenant.id,
        knowledge_base_id=kb.id,
        title=doc_title,
        source=doc_source,
        extra_metadata={"original_filename": filename, "file_size": file_size},
        raw_content=content,  # 保存原始内容
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    return GroundDocumentResponse(
        id=doc.id,
        title=doc.title,
        source=doc.source,
        file_size=file_size,
    )


# ==================== Ground 入库 API ====================
from app.schemas.internal import IngestionParams
from app.services.ingestion import ingest_document
from app.pipeline import operator_registry
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


class GroundIngestRequest(BaseModel):
    """Ground 入库请求"""
    target_kb_name: str  # 目标知识库名称
    target_kb_description: str | None = None
    # 配置覆盖
    chunker: dict | None = None  # {"name": "recursive", "params": {...}}
    indexer: dict | None = None  # {"name": "raptor", "params": {...}}
    enricher: dict | None = None  # {"name": "summary", "params": {...}}
    generate_summary: bool = False
    enrich_chunks: bool = False
    embedding_provider: str | None = None
    embedding_model: str | None = None
    # 可选：为 embedding 提供专用的 key/base_url（未提供时使用系统/环境配置）
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    # 可选：为文档增强（摘要/Chunk增强）提供 LLM 配置（未提供时使用系统/环境配置）
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None


class GroundIngestResult(BaseModel):
    """单个文档入库结果"""
    title: str
    document_id: str | None = None
    chunk_count: int | None = None
    success: bool
    error: str | None = None


class GroundIngestResponse(BaseModel):
    """Ground 入库响应"""
    knowledge_base_id: str
    knowledge_base_name: str
    results: list[GroundIngestResult]
    total: int
    succeeded: int
    failed: int


@router.post("/{ground_id}/ingest", response_model=GroundIngestResponse)
async def ingest_ground_to_kb(
    ground_id: str,
    payload: GroundIngestRequest,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    将 Ground 中的所有文档入库到新知识库
    
    此接口会：
    1. 创建一个新的知识库
    2. 读取 Ground 中所有文档的原始内容
    3. 使用指定的配置（chunker、enricher 等）进行入库
    4. 返回入库结果
    """
    # 获取 ground 对应的知识库
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    ground_kb = None
    for k in result.scalars().all():
        cfg = k.config or {}
        if cfg.get("ground_id") == ground_id:
            ground_kb = k
            break
    
    if not ground_kb:
        raise HTTPException(status_code=404, detail={"code": "GROUND_NOT_FOUND", "detail": "Ground not found"})
    
    # 获取 Ground 中的所有文档
    doc_result = await db.execute(
        select(Document).where(Document.knowledge_base_id == ground_kb.id)
    )
    ground_docs = doc_result.scalars().all()
    
    if not ground_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_DOCUMENTS", "detail": "Ground 中没有文档"}
        )
    
    # 在开始入库前把文档字段提取成普通字典，避免后续 commit 使 ORM 对象过期后再触发懒加载
    ground_doc_payloads = [
        {
            "title": doc.title,
            "raw_content": doc.raw_content,
            "extra_metadata": doc.extra_metadata,
            "source": doc.source,
        }
        for doc in ground_docs
    ]
    
    # 验证 chunker 配置
    if payload.chunker:
        chunker_name = payload.chunker.get("name", "recursive")
        if chunker_name not in operator_registry.list("chunker"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_CHUNKER",
                    "detail": f"未知 chunker: {chunker_name}，可用: {operator_registry.list('chunker')}"
                },
            )
    
    # 检查知识库名称是否已存在
    existing_kb = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant.id,
            KnowledgeBase.name == payload.target_kb_name,
        )
    )
    if existing_kb.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "KB_NAME_EXISTS",
                "detail": f"知识库名称「{payload.target_kb_name}」已存在，请使用其他名称"
            }
        )
    
    # 创建目标知识库
    target_kb_config: dict = {}
    if payload.chunker:
        if "ingestion" not in target_kb_config:
            target_kb_config["ingestion"] = {}
        target_kb_config["ingestion"]["chunker"] = {
            "name": payload.chunker.get("name", "recursive"),
            "params": payload.chunker.get("params", {}),
        }
    if payload.indexer:
        if "ingestion" not in target_kb_config:
            target_kb_config["ingestion"] = {}
        target_kb_config["ingestion"]["indexer"] = {
            "name": payload.indexer.get("name", "standard"),
            "params": payload.indexer.get("params", {}),
        }
    if payload.enricher or payload.generate_summary or payload.enrich_chunks:
        if "ingestion" not in target_kb_config:
            target_kb_config["ingestion"] = {}
        target_kb_config["ingestion"]["enricher"] = {
            "name": payload.enricher.get("name", "none") if payload.enricher else "none",
            "params": payload.enricher.get("params", {}) if payload.enricher else {},
            "generate_summary": payload.generate_summary,
            "enrich_chunks": payload.enrich_chunks,
        }
    if payload.embedding_provider and payload.embedding_model:
        target_kb_config["embedding"] = {
            "provider": payload.embedding_provider,
            "model": payload.embedding_model,
        }
    
    target_kb = KnowledgeBase(
        tenant_id=tenant.id,
        name=payload.target_kb_name,
        description=payload.target_kb_description,
        config=target_kb_config if target_kb_config else None,
    )
    db.add(target_kb)
    await db.commit()
    await db.refresh(target_kb)
    # 缓存知识库标识，避免后续 rollback 导致 ORM 对象过期再触发懒加载
    target_kb_id = target_kb.id
    target_kb_name = target_kb.name
    
    # 验证 embedding 配置（提前检查，避免后台任务失败）
    embedding_config: dict | None = None
    if payload.embedding_provider and payload.embedding_model:
        settings = get_settings()
        try:
            embedding_config = settings._get_provider_config(
                payload.embedding_provider,
                payload.embedding_model
            )
            if payload.embedding_api_key is not None:
                embedding_config["api_key"] = payload.embedding_api_key
            if payload.embedding_base_url and payload.embedding_base_url.strip():
                embedding_config["base_url"] = payload.embedding_base_url.strip()
            needs_key = payload.embedding_provider.lower() in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi", "gemini")
            if needs_key and not embedding_config.get("api_key"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "EMBEDDING_API_KEY_MISSING",
                        "detail": f"{payload.embedding_provider.upper()}_API_KEY 未配置，请在 .env/环境变量中设置，或在请求中提供 embedding_api_key",
                    },
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_EMBEDDING_CONFIG", "detail": str(e)}
            )
    
    # 【关键改动】立即为每个 Ground 文档创建 Document 记录（状态为 processing）
    results: list[GroundIngestResult] = []
    doc_id_mapping: dict[str, str] = {}  # title -> doc_id 映射，用于后台任务
    
    for doc_data in ground_doc_payloads:
        doc_title = doc_data["title"]
        doc_raw_content = doc_data["raw_content"]
        doc_extra_metadata = doc_data["extra_metadata"]
        doc_source = doc_data["source"]
        
        if not doc_raw_content:
            results.append(GroundIngestResult(
                title=doc_title,
                success=False,
                error="文档没有原始内容",
            ))
            continue
        
        # 创建 Document 记录（状态为 processing，chunk_count 暂为 0）
        new_doc = Document(
            tenant_id=tenant.id,
            knowledge_base_id=target_kb_id,
            title=doc_title,
            source=doc_source,
            raw_content=doc_raw_content,
            extra_metadata=doc_extra_metadata,
            summary_status="pending",
            processing_log="[等待处理] 文档已创建，正在排队入库...\n",
        )
        db.add(new_doc)
        await db.flush()
        
        doc_id_mapping[doc_title] = new_doc.id
        results.append(GroundIngestResult(
            title=doc_title,
            document_id=new_doc.id,
            chunk_count=0,  # 暂时为 0，后台任务完成后会更新
            success=True,  # 记录创建成功，入库在后台进行
        ))
    
    await db.commit()
    
    # 记录日志
    logger.info(f"Ground {ground_id} 快速响应: 创建 {len(doc_id_mapping)} 个文档记录，开始后台入库")
    
    # 【关键改动】启动后台任务执行实际入库
    asyncio.create_task(
        _background_ingest_documents(
            tenant_id=tenant.id,
            kb_id=target_kb_id,
            doc_id_mapping=doc_id_mapping,
            ground_doc_payloads=ground_doc_payloads,
            payload=payload,
            embedding_config=embedding_config,
        )
    )
    
    # 立即返回响应
    return GroundIngestResponse(
        knowledge_base_id=target_kb_id,
        knowledge_base_name=target_kb_name,
        results=results,
        total=len(ground_doc_payloads),
        succeeded=len(doc_id_mapping),
        failed=len(ground_doc_payloads) - len(doc_id_mapping),
    )


async def _background_ingest_documents(
    tenant_id: str,
    kb_id: str,
    doc_id_mapping: dict[str, str],
    ground_doc_payloads: list[dict],
    payload: GroundIngestRequest,
    embedding_config: dict | None,
):
    """
    后台任务：执行实际的文档入库（chunking、embedding、写入向量库）
    
    此函数在独立的数据库会话中运行，不影响主请求的响应速度。
    """
    from datetime import datetime
    
    logger.info(f"后台入库任务开始: kb={kb_id}, 文档数={len(doc_id_mapping)}")
    
    async with SessionLocal() as db:
        # 获取知识库
        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        target_kb = kb_result.scalar_one_or_none()
        if not target_kb:
            logger.error(f"后台入库失败: 知识库 {kb_id} 不存在")
            return
        
        succeeded = 0
        failed = 0
        
        for doc_data in ground_doc_payloads:
            doc_title = doc_data["title"]
            doc_id = doc_id_mapping.get(doc_title)
            
            if not doc_id:
                # 该文档在创建阶段就失败了，跳过
                continue
            
            doc_raw_content = doc_data["raw_content"]
            doc_extra_metadata = doc_data["extra_metadata"]
            doc_source = doc_data["source"]
            
            # 获取文档记录
            doc_result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = doc_result.scalar_one_or_none()
            if not doc:
                logger.warning(f"后台入库: 文档 {doc_id} 不存在，跳过")
                failed += 1
                continue
            
            try:
                # 更新日志：开始处理
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                doc.processing_log = f"[{ts}] [INFO] 开始处理文档: {doc_title}\n"
                await db.flush()
                
                # 构建 LLM 配置
                llm_config = None
                if payload.llm_provider:
                    llm_config = {
                        "provider": payload.llm_provider,
                        "model": payload.llm_model,
                        "api_key": payload.llm_api_key,
                        "base_url": payload.llm_base_url,
                    }
                
                # 调用入库服务（使用已存在的文档记录）
                params = IngestionParams(
                    title=doc_title,
                    content=doc_raw_content,
                    metadata=doc_extra_metadata,
                    source=doc_source,
                    generate_doc_summary=payload.generate_summary,
                    enrich_chunks=payload.enrich_chunks,
                    llm_config=llm_config,
                    enricher_config=payload.enricher,
                    indexer_config=payload.indexer,
                    existing_doc_id=doc_id,  # 传入已存在的文档 ID
                )
                ingest_result = await ingest_document(
                    db,
                    tenant_id=tenant_id,
                    kb=target_kb,
                    params=params,
                    embedding_config=embedding_config,
                )
                
                # 检查向量库写入是否成功
                qdrant_result = next(
                    (r for r in ingest_result.indexing_results if r.store_type == "qdrant"),
                    None
                )
                if qdrant_result and not qdrant_result.success:
                    await db.rollback()
                    # 更新文档状态为失败
                    doc_result2 = await db.execute(select(Document).where(Document.id == doc_id))
                    doc2 = doc_result2.scalar_one_or_none()
                    if doc2:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        doc2.processing_log = (doc2.processing_log or "") + f"[{ts}] [ERROR] 向量索引失败: {qdrant_result.error}\n"
                        doc2.summary_status = "failed"
                        await db.commit()
                    failed += 1
                    continue
                
                await db.commit()
                succeeded += 1
                logger.info(f"后台入库成功: {doc_title}, chunks={len(ingest_result.chunks)}")
                
            except Exception as e:
                logger.warning(f"后台入库文档 '{doc_title}' 失败: {e}")
                await db.rollback()
                
                # 更新文档状态为失败
                try:
                    doc_result3 = await db.execute(select(Document).where(Document.id == doc_id))
                    doc3 = doc_result3.scalar_one_or_none()
                    if doc3:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        doc3.processing_log = (doc3.processing_log or "") + f"[{ts}] [ERROR] 入库失败: {str(e)}\n"
                        doc3.summary_status = "failed"
                        await db.commit()
                except Exception:
                    pass
                
                failed += 1
        
        logger.info(f"后台入库任务完成: kb={kb_id}, 成功={succeeded}, 失败={failed}")
