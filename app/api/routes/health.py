"""
健康检查接口

用于 Kubernetes 等容器编排系统进行存活探测和就绪探测。
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthcheck() -> dict:
    """
    健康检查端点
    
    返回 {"status": "ok"} 表示服务正常运行。
    可扩展为检查数据库连接、向量库连接等。
    """
    return {"status": "ok"}
