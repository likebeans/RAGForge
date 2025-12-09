"""
知识库管理接口

提供知识库的 CRUD 操作，包括创建、查询、更新、删除。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant, require_role
from app.auth.api_key import APIKeyContext
from app.exceptions import KBConfigError
from app.infra.vector_store import vector_store
from app.infra.bm25_store import bm25_store
from app.models import Chunk, Document, KnowledgeBase
from app.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.services.config_validation import (
    ConfigValidationError,
    validate_embedding_config_compatibility,
    validate_kb_config,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/knowledge-bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建知识库
    
    在当前租户下创建一个新的知识库。
    知识库名称在租户内必须唯一。
    """
    # 检查同名知识库是否已存在
    exists = await db.execute(
        select(KnowledgeBase.id).where(
            KnowledgeBase.tenant_id == tenant.id,
            KnowledgeBase.name == payload.name,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "detail": "Knowledge base name already exists"},
        )

    # 创建知识库记录
    cfg = payload.config.model_dump(exclude_none=True) if payload.config else {}
    if cfg:
        try:
            validate_kb_config(cfg)
        except ConfigValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "KB_CONFIG_ERROR", "detail": str(e)},
            )

    kb = KnowledgeBase(
        tenant_id=tenant.id,
        name=payload.name,
        description=payload.description,
        config=cfg,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)  # 刷新获取数据库生成的字段（如 id、created_at）
    return kb


@router.get("/v1/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )
    return kb


@router.get("/v1/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    page: int = Query(1, ge=1, description="页码（>=1）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（1-100）"),
    include_ground: bool = Query(False, description="是否包含 Ground 临时知识库"),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    列出当前租户的所有知识库
    """
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.tenant_id == tenant.id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    all_kbs = result.scalars().all()
    if not include_ground:
        all_kbs = [kb for kb in all_kbs if not ((kb.config or {}).get("is_ground") and (kb.config or {}).get("ground_id"))]

    total = len(all_kbs)
    start = (page - 1) * page_size
    end = start + page_size
    kbs = all_kbs[start:end]

    pages = (total + page_size - 1) // page_size if total is not None else 0
    return KnowledgeBaseListResponse(
        items=list(kbs),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.patch("/v1/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    payload: KnowledgeBaseUpdate,
    kb_id: str,
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    if payload.name is not None:
        kb.name = payload.name
    if payload.description is not None:
        kb.description = payload.description
    if payload.config is not None:
        # 检查知识库是否有文档
        doc_count_result = await db.execute(
            select(func.count()).select_from(
                select(Document.id).where(Document.knowledge_base_id == kb_id).subquery()
            )
        )
        has_documents = doc_count_result.scalar_one() > 0
        
        # 转换 Pydantic 对象为字典
        new_config = payload.config.model_dump(exclude_none=True)
        
        try:
            # 校验基本配置
            validate_kb_config(new_config)
            # 校验 embedding 配置变更兼容性
            validate_embedding_config_compatibility(
                old_config=kb.config,
                new_config=new_config,
                has_documents=has_documents,
            )
        except ConfigValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "KB_CONFIG_ERROR", "detail": str(e)},
            )
        kb.config = new_config

    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.delete("/v1/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除知识库及其所有文档和向量

    处理流程：
    1. 验证知识库存在且属于当前租户
    2. 删除向量数据库中该知识库的所有向量
    3. 删除数据库中的 Chunks
    4. 删除数据库中的 Documents
    5. 删除数据库中的 KnowledgeBase
    """
    # 验证知识库归属
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "KB_NOT_FOUND", "detail": "Knowledge base not found"},
        )

    # 获取该知识库下所有文档的 ID
    doc_result = await db.execute(
        select(Document.id).where(Document.knowledge_base_id == kb_id)
    )
    doc_ids = [row[0] for row in doc_result.fetchall()]

    # 获取该知识库下所有 Chunk 的 ID（用于删除向量）
    if doc_ids:
        chunk_result = await db.execute(
            select(Chunk.id).where(Chunk.document_id.in_(doc_ids))
        )
        chunk_ids = [row[0] for row in chunk_result.fetchall()]

        # 删除向量数据库中的向量
        if chunk_ids:
            try:
                await vector_store.delete_by_ids(tenant.id, chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} vectors for kb {kb_id}")
            except Exception as e:
                logger.warning(f"Failed to delete vectors for kb {kb_id}: {e}")

        # 删除 Chunks
        await db.execute(delete(Chunk).where(Chunk.document_id.in_(doc_ids)))

        # 删除 Documents
        await db.execute(delete(Document).where(Document.knowledge_base_id == kb_id))

    # 删除 KnowledgeBase
    await db.delete(kb)
    bm25_store.delete_by_kb(tenant_id=tenant.id, knowledge_base_id=kb_id)
    await db.commit()

    logger.info(f"Deleted knowledge base {kb_id} with {len(doc_ids)} documents")
