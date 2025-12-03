"""
结构化日志配置

提供 JSON 格式的结构化日志，支持请求追踪和可观测性。

功能：
- JSON 格式输出，便于日志聚合（ELK/Loki）
- 请求 ID 追踪（X-Request-ID）
- 租户 ID 关联
- 性能指标记录

使用示例：
    from app.infra.logging import setup_logging, get_logger
    
    # 应用启动时配置
    setup_logging()
    
    # 获取 logger
    logger = get_logger(__name__)
    logger.info("处理请求", extra={"tenant_id": "xxx", "action": "retrieve"})
"""

import logging
import sys
import json
import time
from datetime import datetime, timezone
from typing import Any
from contextvars import ContextVar

from app.config import get_settings

# 请求上下文变量
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def get_request_id() -> str | None:
    """获取当前请求 ID"""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求 ID"""
    request_id_var.set(request_id)


def get_tenant_id() -> str | None:
    """获取当前租户 ID"""
    return tenant_id_var.get()


def set_tenant_id(tenant_id: str) -> None:
    """设置当前租户 ID"""
    tenant_id_var.set(tenant_id)


class JSONFormatter(logging.Formatter):
    """
    JSON 格式日志格式化器
    
    输出格式：
    {
        "timestamp": "2024-01-01T00:00:00.000Z",
        "level": "INFO",
        "logger": "app.services.query",
        "message": "检索完成",
        "request_id": "abc123",
        "tenant_id": "tenant_001",
        "extra": {...}
    }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加请求上下文
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id
        
        tenant_id = get_tenant_id()
        if tenant_id:
            log_data["tenant_id"] = tenant_id
        
        # 添加源代码位置（仅 DEBUG 级别）
        if record.levelno <= logging.DEBUG:
            log_data["location"] = f"{record.pathname}:{record.lineno}"
        
        # 添加 extra 字段（排除标准字段）
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "taskName", "message",
        }
        extra = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        if extra:
            log_data["extra"] = extra
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    控制台友好的日志格式化器（开发环境）
    
    输出格式：
    2024-01-01 00:00:00 INFO [request_id] logger_name - message
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        color = self.COLORS.get(level, "")
        
        # 构建前缀
        parts = [f"{timestamp} {color}{level:8}{self.RESET}"]
        
        request_id = get_request_id()
        if request_id:
            parts.append(f"[{request_id[:8]}]")
        
        parts.append(f"{record.name} -")
        parts.append(record.getMessage())
        
        result = " ".join(parts)
        
        # 添加异常信息
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)
        
        return result


def setup_logging(
    level: str | None = None,
    json_format: bool | None = None,
) -> None:
    """
    配置应用日志
    
    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR），默认从配置读取
        json_format: 是否使用 JSON 格式，默认生产环境使用 JSON
    """
    settings = get_settings()
    
    # 确定日志级别
    if level is None:
        level = getattr(settings, "log_level", "INFO")
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 确定格式
    if json_format is None:
        json_format = settings.environment not in ("dev", "development", "test")
    
    # 创建处理器
    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())
    
    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # 降低第三方库日志级别
    for noisy_logger in (
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "sqlalchemy.engine",
        "qdrant_client",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    
    logging.getLogger("app").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """
    获取 logger 实例
    
    Args:
        name: logger 名称，通常使用 __name__
    
    Returns:
        配置好的 logger 实例
    """
    return logging.getLogger(name)


class RequestTimer:
    """
    请求计时器，用于记录请求耗时
    
    使用示例：
        timer = RequestTimer()
        timer.mark("embedding")
        # ... 执行 embedding
        timer.mark("search")
        # ... 执行 search
        metrics = timer.get_metrics()
        # {"total_ms": 150, "embedding_ms": 50, "search_ms": 100}
    """
    
    def __init__(self):
        self.start_time = time.perf_counter()
        self.marks: list[tuple[str, float]] = []
        self._last_mark = self.start_time
    
    def mark(self, name: str) -> None:
        """记录一个时间点"""
        now = time.perf_counter()
        self.marks.append((name, now - self._last_mark))
        self._last_mark = now
    
    def get_metrics(self) -> dict[str, float]:
        """
        获取耗时指标
        
        Returns:
            包含各阶段耗时的字典（毫秒）
        """
        total = time.perf_counter() - self.start_time
        metrics = {"total_ms": round(total * 1000, 2)}
        for name, duration in self.marks:
            metrics[f"{name}_ms"] = round(duration * 1000, 2)
        return metrics
