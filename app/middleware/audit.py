"""
审计日志中间件

自动记录关键 API 调用到审计日志表。

功能：
- 记录检索、RAG、文档上传等关键操作
- 异步写入，不影响响应时间
- 自动提取租户信息
"""

import time
import asyncio
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infra.logging import get_request_id, get_logger
from app.db.session import SessionLocal
from app.services.audit import record_audit_log

logger = get_logger(__name__)

# 需要审计的路径模式
AUDIT_PATHS = {
    "/v1/retrieve": "retrieve",
    "/v1/rag": "rag",
    "/v1/chat/completions": "rag_chat",
    "/v1/embeddings": "embedding",
    "/v1/knowledge-bases": "kb",
    "/v1/api-keys": "apikey",
    "/admin/tenants": "admin_tenant",
    "/admin": "admin_generic",
    "/documents": "document",
}


def _get_action_from_path(method: str, path: str) -> str | None:
    """根据路径和方法确定操作类型"""
    for pattern, action_prefix in AUDIT_PATHS.items():
        if pattern in path:
            if method == "POST":
                if action_prefix == "retrieve":
                    return "retrieve"
                elif action_prefix == "rag":
                    return "rag"
                elif action_prefix == "rag_chat":
                    return "rag_chat"
                elif action_prefix == "embedding":
                    return "embedding"
                elif action_prefix == "kb":
                    return "kb_create"
                elif action_prefix == "apikey":
                    return "apikey_create"
                elif action_prefix == "admin_tenant":
                    return "admin_tenant_create"
                elif action_prefix == "admin_generic":
                    return "admin_action"
                elif action_prefix == "document":
                    return "doc_upload"
            elif method == "DELETE":
                if action_prefix == "kb":
                    return "kb_delete"
                elif action_prefix == "document":
                    return "doc_delete"
                elif action_prefix == "apikey":
                    return "apikey_delete"
                elif action_prefix in ("admin_tenant", "admin_generic"):
                    return "admin_delete"
            elif method == "GET":
                return f"{action_prefix}_read"
            elif method in ("PATCH", "PUT"):
                if action_prefix == "kb":
                    return "kb_update"
                elif action_prefix == "document":
                    return "doc_update"
                elif action_prefix == "apikey":
                    return "apikey_update"
                elif action_prefix.startswith("admin"):
                    return "admin_update"
    return None


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    审计日志中间件
    
    - 记录关键 API 操作
    - 异步写入数据库
    - 不阻塞响应
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 判断是否需要审计
        action = _get_action_from_path(request.method, request.url.path)
        if not action:
            return await call_next(request)
        
        # 获取请求信息
        request_id = get_request_id() or "unknown"
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000
        
        # 从 request.state 获取认证信息（由认证中间件设置）
        tenant_id = getattr(request.state, "tenant_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)
        
        # 异步记录审计日志（不阻塞响应）
        asyncio.create_task(
            self._record_audit(
                request_id=request_id,
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                action=action,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        )
        
        return response
    
    async def _record_audit(
        self,
        request_id: str,
        tenant_id: str | None,
        api_key_id: str | None,
        action: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        ip_address: str | None,
        user_agent: str | None,
    ):
        """异步记录审计日志"""
        try:
            async with SessionLocal() as session:
                await record_audit_log(
                    session=session,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    api_key_id=api_key_id,
                    action=action,
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                await session.commit()
        except Exception as e:
            # 审计日志写入失败不应影响业务
            logger.warning(f"审计日志写入失败: {e}")
