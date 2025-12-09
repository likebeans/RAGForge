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
