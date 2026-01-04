"""
健康检查和运维接口

提供：
- /health: 基础存活检查（Kubernetes liveness probe）
- /ready: 就绪检查（Kubernetes readiness probe）
- /metrics: 系统指标
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import SessionLocal
from app.config import get_settings
from app.infra.metrics import metrics_collector
from app.infra.bm25_store import bm25_store

router = APIRouter()

# 服务启动时间
_start_time = time.time()


async def _check_database() -> tuple[bool, str]:
    """检查数据库连接"""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as e:
        return False, str(e)


async def _check_qdrant() -> tuple[bool, str]:
    """检查 Qdrant 连接"""
    try:
        from app.infra.vector_store import vector_store
        # 尝试获取集合列表
        collections = await vector_store.client.get_collections()
        return True, f"connected ({len(collections.collections)} collections)"
    except Exception as e:
        return False, str(e)

async def _check_es() -> tuple[bool, str]:
    """检查 ES/OpenSearch 连接（仅当 bm25_backend=es 且启用时）"""
    try:
        if not getattr(bm25_store, "enabled", False):
            return True, "disabled"
        if getattr(bm25_store, "backend_name", "memory") != "es":
            return True, "using memory"
        backend = bm25_store.backend
        ping = await backend.client.ping()
        return (True, "connected") if ping else (False, "ping failed")
    except Exception as e:
        return False, str(e)


@router.get("/health")
async def healthcheck() -> dict:
    """
    基础存活检查（Liveness Probe）
    
    仅检查服务是否在运行，不检查依赖服务。
    用于 Kubernetes liveness probe。
    """
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    就绪检查（Readiness Probe）
    
    检查所有依赖服务是否可用：
    - PostgreSQL 数据库
    - Qdrant 向量库
    
    返回 200 表示服务就绪可接收流量。
    返回 503 表示服务未就绪。
    """
    checks = {}
    all_healthy = True
    
    # 检查数据库
    db_ok, db_msg = await _check_database()
    checks["database"] = {"status": "ok" if db_ok else "error", "message": db_msg}
    if not db_ok:
        all_healthy = False
    
    # 检查 Qdrant
    qdrant_ok, qdrant_msg = await _check_qdrant()
    checks["qdrant"] = {"status": "ok" if qdrant_ok else "error", "message": qdrant_msg}
    if not qdrant_ok:
        all_healthy = False

    # 检查 ES/OpenSearch（可选）
    es_ok, es_msg = await _check_es()
    checks["es"] = {"status": "ok" if es_ok else "error", "message": es_msg}
    if not es_ok:
        all_healthy = False
    
    response = {
        "status": "ok" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    status_code = 200 if all_healthy else 503
    return JSONResponse(content=response, status_code=status_code)


@router.get("/metrics")
async def get_metrics() -> dict:
    """
    系统指标端点
    
    返回：
    - 服务运行时间
    - 调用统计（LLM/Embedding/Rerank）
    - 检索统计
    - 配置信息
    """
    settings = get_settings()
    uptime_seconds = time.time() - _start_time
    
    # 获取聚合统计
    stats = metrics_collector.get_stats()
    
    return {
        "service": {
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_human": _format_uptime(uptime_seconds),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "config": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "embedding_dim": settings.embedding_dim,
            "rerank_provider": settings.rerank_provider,
            "bm25_backend": getattr(bm25_store, "backend_name", "memory"),
            "bm25_enabled": getattr(bm25_store, "enabled", True),
            "es_index_mode": settings.es_index_mode,
        },
        "stats": stats,
        "bm25_backends": stats.get("retrieval_backends", {}),
    }


def _format_uptime(seconds: float) -> str:
    """格式化运行时间"""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    
    return " ".join(parts)
