"""
请求追踪中间件

为每个请求生成唯一 ID，支持全链路追踪。

功能：
- 生成或接收 X-Request-ID
- 在响应头中返回 request_id
- 设置请求上下文供日志使用
- 记录请求耗时

使用示例：
    from app.middleware.request_trace import RequestTraceMiddleware
    
    app.add_middleware(RequestTraceMiddleware)
"""

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infra.logging import (
    set_request_id,
    set_tenant_id,
    get_logger,
    RequestTimer,
)

logger = get_logger(__name__)


class RequestTraceMiddleware(BaseHTTPMiddleware):
    """
    请求追踪中间件
    
    - 从 X-Request-ID 头获取请求 ID，或自动生成
    - 在响应中返回 X-Request-ID 和 X-Response-Time
    - 记录请求日志（路径、方法、耗时、状态码）
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取或生成 request_id
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        
        # 开始计时
        timer = RequestTimer()
        
        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            metrics = timer.get_metrics()
            logger.error(
                f"{request.method} {request.url.path} - 500 - {metrics['total_ms']:.0f}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": metrics["total_ms"],
                    "error": str(e),
                },
            )
            raise
        
        # 记录请求日志
        metrics = timer.get_metrics()
        log_extra = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": metrics["total_ms"],
        }
        
        # 根据状态码选择日志级别
        if response.status_code >= 500:
            logger.error(
                f"{request.method} {request.url.path} - {response.status_code} - {metrics['total_ms']:.0f}ms",
                extra=log_extra,
            )
        elif response.status_code >= 400:
            logger.warning(
                f"{request.method} {request.url.path} - {response.status_code} - {metrics['total_ms']:.0f}ms",
                extra=log_extra,
            )
        else:
            # 跳过高频低价值请求的日志（健康检查、轮询请求等）
            skip_paths = ("/health", "/metrics", "/favicon.ico")
            # 轮询请求模式：GET /v1/documents/{id} 和 GET /v1/knowledge-bases/{id}/documents
            is_polling = (
                request.method == "GET" and 
                (request.url.path.startswith("/v1/documents/") or 
                 request.url.path.endswith("/documents"))
            )
            if request.url.path not in skip_paths and not is_polling:
                logger.info(
                    f"{request.method} {request.url.path} - {response.status_code} - {metrics['total_ms']:.0f}ms",
                    extra=log_extra,
                )
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{metrics['total_ms']:.0f}ms"
        
        return response
