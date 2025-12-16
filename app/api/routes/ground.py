"""
Ground (Playground 临时知识库) API

Ground 会创建一个临时知识库，用于实验流程，支持保存为正式知识库或删除。
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant, require_role
from app.auth.api_key import APIKeyContext
from app.models import KnowledgeBase, Document, Chunk
from app.infra.vector_store import vector_store
from app.infra.bm25_store import bm25_store
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
    bm25_store.delete_by_kb(tenant_id=tenant.id, knowledge_base_id=kb.id)
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
        raise HTTPException(status_code=404, detail="Ground not found")
    
    # 获取文档
    doc_result = await db.execute(
        select(Document).where(
            Document.id == payload.document_id,
            Document.knowledge_base_id == kb.id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 从 raw_content 获取原始文件内容
    content = doc.raw_content or ""
    if not content:
        raise HTTPException(status_code=400, detail="Document has no raw content. Please re-upload the file.")
    
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
        raise HTTPException(status_code=404, detail="Ground not found")
    
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
        raise HTTPException(status_code=404, detail="Ground not found")
    
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
    
    # 入库所有文档
    results: list[GroundIngestResult] = []
    succeeded = 0
    failed = 0
    
    # 构建 embedding 配置（优先使用前端传入的配置）
    embedding_config: dict | None = None
    if payload.embedding_provider and payload.embedding_model:
        settings = get_settings()
        try:
            embedding_config = settings._get_provider_config(
                payload.embedding_provider,
                payload.embedding_model
            )
            # 覆盖用户传入的 key/base_url（前端若未传，则继续使用系统/环境配置）
            if payload.embedding_api_key is not None:
                embedding_config["api_key"] = payload.embedding_api_key
            if payload.embedding_base_url is not None:
                embedding_config["base_url"] = payload.embedding_base_url
            # 若仍缺少 api_key，提前报错，提示配置来源
            needs_key = payload.embedding_provider.lower() in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi", "gemini")
            if needs_key and not embedding_config.get("api_key"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "EMBEDDING_API_KEY_MISSING",
                        "detail": f"{payload.embedding_provider.upper()}_API_KEY 未配置，请在 .env/环境变量中设置，或在请求中提供 embedding_api_key",
                    },
                )
            # 记录详细入库配置
            chunker_info = f"{payload.chunker.get('name')}" if payload.chunker else "默认"
            indexer_info = f"{payload.indexer.get('name')}" if payload.indexer else "standard"
            enricher_info = f"{payload.enricher.get('name')}" if payload.enricher else "none"
            enrichment_flags = []
            if payload.generate_summary:
                enrichment_flags.append("摘要")
            if payload.enrich_chunks:
                enrichment_flags.append("Chunk增强")
            enrichment_str = "+".join(enrichment_flags) if enrichment_flags else "无"
            logger.info(
                f"Ground 入库配置: embedding={payload.embedding_provider}/{payload.embedding_model}, "
                f"chunker={chunker_info}, indexer={indexer_info}, enricher={enricher_info}, "
                f"enrichment_flags={enrichment_str}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_EMBEDDING_CONFIG", "detail": str(e)}
            )
    
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
            failed += 1
            continue
        
        try:
            # 构建 LLM 配置（用于文档增强）
            llm_config = None
            if payload.llm_provider:
                llm_config = {
                    "provider": payload.llm_provider,
                    "model": payload.llm_model,
                    "api_key": payload.llm_api_key,
                    "base_url": payload.llm_base_url,
                }
            
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
            )
            ingest_result = await ingest_document(
                db,
                tenant_id=tenant.id,
                kb=target_kb,
                params=params,
                embedding_config=embedding_config,
            )
            
            # 检查向量库写入是否成功（核心索引）
            qdrant_result = next(
                (r for r in ingest_result.indexing_results if r.store_type == "qdrant"),
                None
            )
            if qdrant_result and not qdrant_result.success:
                # 向量库写入失败，回滚并标记失败
                await db.rollback()
                results.append(GroundIngestResult(
                    title=doc_title,
                    success=False,
                    error=f"向量索引失败: {qdrant_result.error}",
                ))
                failed += 1
                continue
            
            await db.commit()
            
            results.append(GroundIngestResult(
                title=doc_title,
                document_id=ingest_result.document.id,
                chunk_count=len(ingest_result.chunks),
                success=True,
            ))
            succeeded += 1
        except Exception as e:
            logger.warning(f"入库文档 '{doc_title}' 失败: {e}")
            await db.rollback()
            # rollback 会使 ORM 对象过期，刷新保持后续迭代可用
            try:
                await db.refresh(target_kb)
            except Exception:
                pass
            results.append(GroundIngestResult(
                title=doc_title,
                success=False,
                error=str(e),
            ))
            failed += 1
    
    logger.info(f"Ground {ground_id} 入库完成: {succeeded} 成功, {failed} 失败")
    return GroundIngestResponse(
        knowledge_base_id=target_kb_id,
        knowledge_base_name=target_kb_name,
        results=results,
        total=len(ground_docs),
        succeeded=succeeded,
        failed=failed,
    )
