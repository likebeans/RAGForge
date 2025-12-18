"""
RAPTOR API 端点

提供 RAPTOR 索引的构建和状态查询接口。

端点：
- POST /v1/knowledge-bases/{kb_id}/raptor/build  - 手动触发 RAPTOR 索引构建
- GET  /v1/knowledge-bases/{kb_id}/raptor/status - 查询 RAPTOR 索引状态
- DELETE /v1/knowledge-bases/{kb_id}/raptor      - 删除 RAPTOR 索引
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_tenant
from app.models import Tenant
from app.models.knowledge_base import KnowledgeBase
from app.models.raptor_node import RaptorNode
from app.models.chunk import Chunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/knowledge-bases", tags=["raptor"])


# ============ Schemas ============

class RaptorBuildRequest(BaseModel):
    """RAPTOR 构建请求"""
    max_layers: int = Field(default=3, ge=1, le=5, description="最大层数")
    cluster_method: str = Field(default="gmm", description="聚类方法 (gmm/kmeans)")
    min_cluster_size: int = Field(default=3, ge=2, description="最小聚类大小")
    force_rebuild: bool = Field(default=False, description="是否强制重建（删除现有索引）")


class RaptorBuildResponse(BaseModel):
    """RAPTOR 构建响应"""
    status: str = Field(description="构建状态 (started/already_exists/error)")
    message: str = Field(description="状态消息")
    task_id: str | None = Field(default=None, description="后台任务 ID")


class RaptorNodeStats(BaseModel):
    """RAPTOR 节点统计"""
    level: int = Field(description="层级")
    count: int = Field(description="节点数量")


class RaptorStatusResponse(BaseModel):
    """RAPTOR 状态响应"""
    has_index: bool = Field(description="是否有 RAPTOR 索引")
    total_nodes: int = Field(description="总节点数")
    leaf_nodes: int = Field(description="叶子节点数（原始 chunks）")
    summary_nodes: int = Field(description="摘要节点数")
    max_level: int = Field(description="最大层级")
    nodes_by_level: list[RaptorNodeStats] = Field(description="各层级节点统计")
    last_build_time: datetime | None = Field(default=None, description="最后构建时间")
    indexing_status: str = Field(description="索引状态 (none/building/indexed/error)")


class RaptorDeleteResponse(BaseModel):
    """RAPTOR 删除响应"""
    deleted_nodes: int = Field(description="删除的节点数")
    message: str = Field(description="状态消息")


# ============ Helper Functions ============

async def _get_kb_or_404(
    session: AsyncSession,
    tenant_id: str,
    kb_id: str,
) -> KnowledgeBase:
    """获取知识库，不存在则抛出 404"""
    stmt = (
        select(KnowledgeBase)
        .where(KnowledgeBase.tenant_id == tenant_id)
        .where(KnowledgeBase.id == kb_id)
    )
    result = await session.execute(stmt)
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    return kb


async def _get_raptor_stats(
    session: AsyncSession,
    tenant_id: str,
    kb_id: str,
) -> dict[str, Any]:
    """获取 RAPTOR 索引统计信息"""
    # 总节点数
    total_stmt = (
        select(func.count(RaptorNode.id))
        .where(RaptorNode.tenant_id == tenant_id)
        .where(RaptorNode.knowledge_base_id == kb_id)
    )
    total_result = await session.execute(total_stmt)
    total_nodes = total_result.scalar() or 0
    
    if total_nodes == 0:
        return {
            "has_index": False,
            "total_nodes": 0,
            "leaf_nodes": 0,
            "summary_nodes": 0,
            "max_level": 0,
            "nodes_by_level": [],
            "last_build_time": None,
            "indexing_status": "none",
        }
    
    # 各层级统计
    level_stmt = (
        select(RaptorNode.level, func.count(RaptorNode.id))
        .where(RaptorNode.tenant_id == tenant_id)
        .where(RaptorNode.knowledge_base_id == kb_id)
        .group_by(RaptorNode.level)
        .order_by(RaptorNode.level)
    )
    level_result = await session.execute(level_stmt)
    level_stats = [{"level": row[0], "count": row[1]} for row in level_result.all()]
    
    # 计算统计数据
    leaf_nodes = next((s["count"] for s in level_stats if s["level"] == 0), 0)
    summary_nodes = total_nodes - leaf_nodes
    max_level = max(s["level"] for s in level_stats) if level_stats else 0
    
    # 最后构建时间
    time_stmt = (
        select(func.max(RaptorNode.created_at))
        .where(RaptorNode.tenant_id == tenant_id)
        .where(RaptorNode.knowledge_base_id == kb_id)
    )
    time_result = await session.execute(time_stmt)
    last_build_time = time_result.scalar()
    
    # 索引状态
    status_stmt = (
        select(RaptorNode.indexing_status, func.count(RaptorNode.id))
        .where(RaptorNode.tenant_id == tenant_id)
        .where(RaptorNode.knowledge_base_id == kb_id)
        .group_by(RaptorNode.indexing_status)
    )
    status_result = await session.execute(status_stmt)
    status_counts = {row[0]: row[1] for row in status_result.all()}
    
    if status_counts.get("building", 0) > 0:
        indexing_status = "building"
    elif status_counts.get("error", 0) > 0:
        indexing_status = "error"
    elif status_counts.get("indexed", 0) == total_nodes:
        indexing_status = "indexed"
    else:
        indexing_status = "partial"
    
    return {
        "has_index": True,
        "total_nodes": total_nodes,
        "leaf_nodes": leaf_nodes,
        "summary_nodes": summary_nodes,
        "max_level": max_level,
        "nodes_by_level": level_stats,
        "last_build_time": last_build_time,
        "indexing_status": indexing_status,
    }


async def _build_raptor_index_task(
    kb_id: str,
    tenant_id: str,
    config: dict[str, Any],
) -> None:
    """后台任务：构建 RAPTOR 索引"""
    from app.infra.db import async_session_factory
    from app.services.ingestion import _build_raptor_index
    
    logger.info("[RAPTOR-API] 开始后台构建任务: kb_id=%s", kb_id)
    
    async with async_session_factory() as session:
        try:
            # 获取知识库
            kb_stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            kb_result = await session.execute(kb_stmt)
            kb = kb_result.scalar_one_or_none()
            
            if not kb:
                logger.error("[RAPTOR-API] 知识库不存在: %s", kb_id)
                return
            
            # 获取所有 chunks
            chunk_stmt = (
                select(Chunk)
                .where(Chunk.knowledge_base_id == kb_id)
                .where(Chunk.tenant_id == tenant_id)
            )
            chunk_result = await session.execute(chunk_stmt)
            chunks = chunk_result.scalars().all()
            
            if not chunks:
                logger.warning("[RAPTOR-API] 知识库没有 chunks: %s", kb_id)
                return
            
            # 构建 RAPTOR 配置
            raptor_config = {
                "enabled": True,
                "max_layers": config.get("max_layers", 3),
                "cluster_method": config.get("cluster_method", "gmm"),
                "min_cluster_size": config.get("min_cluster_size", 3),
            }
            
            # 获取 embedding 配置
            kb_config = kb.config or {}
            embedding_config = {
                "provider": kb_config.get("embedding_provider", "qwen"),
                "model": kb_config.get("embedding_model", "text-embedding-v3"),
            }
            
            # 调用构建函数
            await _build_raptor_index(
                session=session,
                tenant_id=tenant_id,
                kb_id=kb_id,
                chunks=chunks,
                raptor_config=raptor_config,
                embedding_config=embedding_config,
            )
            
            logger.info("[RAPTOR-API] 后台构建任务完成: kb_id=%s", kb_id)
            
        except Exception as e:
            logger.error("[RAPTOR-API] 后台构建任务失败: %s", e, exc_info=True)


# ============ API Endpoints ============

@router.get("/{kb_id}/raptor/status", response_model=RaptorStatusResponse)
async def get_raptor_status(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
) -> RaptorStatusResponse:
    """
    获取 RAPTOR 索引状态
    
    返回知识库的 RAPTOR 索引统计信息，包括：
    - 是否有索引
    - 节点总数和各层级分布
    - 索引状态（none/building/indexed/error）
    - 最后构建时间
    """
    # 验证知识库存在
    await _get_kb_or_404(db, str(tenant.id), kb_id)
    
    # 获取统计信息
    stats = await _get_raptor_stats(db, str(tenant.id), kb_id)
    
    return RaptorStatusResponse(
        has_index=stats["has_index"],
        total_nodes=stats["total_nodes"],
        leaf_nodes=stats["leaf_nodes"],
        summary_nodes=stats["summary_nodes"],
        max_level=stats["max_level"],
        nodes_by_level=[RaptorNodeStats(**s) for s in stats["nodes_by_level"]],
        last_build_time=stats["last_build_time"],
        indexing_status=stats["indexing_status"],
    )


@router.post("/{kb_id}/raptor/build", response_model=RaptorBuildResponse)
async def build_raptor_index(
    kb_id: str,
    request: RaptorBuildRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
) -> RaptorBuildResponse:
    """
    手动触发 RAPTOR 索引构建
    
    构建过程在后台执行，可通过 /status 端点查询进度。
    
    参数：
    - max_layers: 最大层数（1-5）
    - cluster_method: 聚类方法（gmm/kmeans）
    - min_cluster_size: 最小聚类大小
    - force_rebuild: 是否强制重建（删除现有索引）
    """
    # 验证知识库存在
    kb = await _get_kb_or_404(db, str(tenant.id), kb_id)
    
    # 检查是否已有索引
    stats = await _get_raptor_stats(db, str(tenant.id), kb_id)
    
    if stats["has_index"] and not request.force_rebuild:
        return RaptorBuildResponse(
            status="already_exists",
            message=f"RAPTOR 索引已存在（{stats['total_nodes']} 节点）。使用 force_rebuild=true 强制重建。",
            task_id=None,
        )
    
    # 如果强制重建，先删除现有索引
    if stats["has_index"] and request.force_rebuild:
        delete_stmt = (
            delete(RaptorNode)
            .where(RaptorNode.tenant_id == str(tenant.id))
            .where(RaptorNode.knowledge_base_id == kb_id)
        )
        await db.execute(delete_stmt)
        await db.commit()
        logger.info("[RAPTOR-API] 已删除现有索引: kb_id=%s, nodes=%d", kb_id, stats["total_nodes"])
    
    # 检查是否有 chunks
    chunk_count_stmt = (
        select(func.count(Chunk.id))
        .where(Chunk.knowledge_base_id == kb_id)
        .where(Chunk.tenant_id == str(tenant.id))
    )
    chunk_result = await db.execute(chunk_count_stmt)
    chunk_count = chunk_result.scalar() or 0
    
    if chunk_count == 0:
        raise HTTPException(
            status_code=400,
            detail="知识库没有文档 chunks，请先上传文档",
        )
    
    # 生成任务 ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # 添加后台任务
    config = {
        "max_layers": request.max_layers,
        "cluster_method": request.cluster_method,
        "min_cluster_size": request.min_cluster_size,
    }
    background_tasks.add_task(
        _build_raptor_index_task,
        kb_id=kb_id,
        tenant_id=str(tenant.id),
        config=config,
    )
    
    logger.info(
        "[RAPTOR-API] 已提交构建任务: kb_id=%s, task_id=%s, chunks=%d",
        kb_id, task_id, chunk_count
    )
    
    return RaptorBuildResponse(
        status="started",
        message=f"RAPTOR 索引构建已启动，共 {chunk_count} 个 chunks。使用 /status 端点查询进度。",
        task_id=task_id,
    )


@router.delete("/{kb_id}/raptor", response_model=RaptorDeleteResponse)
async def delete_raptor_index(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
) -> RaptorDeleteResponse:
    """
    删除 RAPTOR 索引
    
    删除知识库的所有 RAPTOR 节点。原始 chunks 不受影响。
    """
    # 验证知识库存在
    await _get_kb_or_404(db, str(tenant.id), kb_id)
    
    # 获取当前节点数
    count_stmt = (
        select(func.count(RaptorNode.id))
        .where(RaptorNode.tenant_id == str(tenant.id))
        .where(RaptorNode.knowledge_base_id == kb_id)
    )
    count_result = await db.execute(count_stmt)
    node_count = count_result.scalar() or 0
    
    if node_count == 0:
        return RaptorDeleteResponse(
            deleted_nodes=0,
            message="知识库没有 RAPTOR 索引",
        )
    
    # 删除所有节点
    delete_stmt = (
        delete(RaptorNode)
        .where(RaptorNode.tenant_id == str(tenant.id))
        .where(RaptorNode.knowledge_base_id == kb_id)
    )
    await db.execute(delete_stmt)
    await db.commit()
    
    logger.info("[RAPTOR-API] 已删除 RAPTOR 索引: kb_id=%s, nodes=%d", kb_id, node_count)
    
    return RaptorDeleteResponse(
        deleted_nodes=node_count,
        message=f"已删除 {node_count} 个 RAPTOR 节点",
    )
