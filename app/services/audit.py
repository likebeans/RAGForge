"""
审计日志服务

提供审计日志的记录和查询功能。

功能：
- 异步记录 API 访问日志
- 支持按租户、时间、操作类型查询
- 敏感信息脱敏

使用示例：
    from app.services.audit import record_audit_log, query_audit_logs
    
    # 记录审计日志
    await record_audit_log(
        session=db,
        request_id="xxx",
        tenant_id="tenant_001",
        action="retrieve",
        ...
    )
    
    # 查询审计日志
    logs = await query_audit_logs(
        session=db,
        tenant_id="tenant_001",
        action="retrieve",
        limit=100,
    )
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.infra.logging import get_logger

logger = get_logger(__name__)


# 需要脱敏的字段
SENSITIVE_FIELDS = {"password", "api_key", "token", "secret", "authorization"}


def _sanitize_data(data: dict | None, max_length: int = 500) -> str | None:
    """
    脱敏处理请求/响应数据
    
    - 移除敏感字段
    - 截断过长内容
    """
    if not data:
        return None
    
    sanitized = {}
    for key, value in data.items():
        # 跳过敏感字段
        if key.lower() in SENSITIVE_FIELDS:
            sanitized[key] = "***"
            continue
        
        # 截断过长的字符串值
        if isinstance(value, str) and len(value) > max_length:
            sanitized[key] = value[:max_length] + "..."
        elif isinstance(value, (list, dict)):
            # 复杂类型只保留摘要
            sanitized[key] = f"<{type(value).__name__} len={len(value)}>"
        else:
            sanitized[key] = value
    
    result = str(sanitized)
    if len(result) > max_length:
        return result[:max_length] + "..."
    return result


async def record_audit_log(
    session: AsyncSession,
    *,
    request_id: str,
    action: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    tenant_id: str | None = None,
    api_key_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    query_params: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_summary: str | None = None,
    response_summary: str | None = None,
    error_message: str | None = None,
    extra_data: dict | None = None,
) -> AuditLog:
    """
    记录审计日志
    
    Args:
        session: 数据库会话
        request_id: 请求唯一标识
        action: 操作类型（retrieve/ingest/rag/kb_create/...）
        method: HTTP 方法
        path: 请求路径
        status_code: 响应状态码
        duration_ms: 请求耗时（毫秒）
        tenant_id: 租户 ID
        api_key_id: API Key ID
        resource_type: 资源类型
        resource_id: 资源 ID
        query_params: 查询参数
        ip_address: 客户端 IP
        user_agent: User-Agent
        request_summary: 请求摘要
        response_summary: 响应摘要
        error_message: 错误信息
        extra_data: 扩展数据
    
    Returns:
        创建的审计日志记录
    """
    log = AuditLog(
        id=str(uuid.uuid4()),
        request_id=request_id,
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        method=method,
        path=path,
        query_params=query_params,
        status_code=status_code,
        duration_ms=duration_ms,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent and len(user_agent) > 500 else user_agent,
        request_summary=request_summary,
        response_summary=response_summary,
        error_message=error_message,
        extra_data=extra_data,
    )
    
    session.add(log)
    # 不立即 commit，由调用方控制事务
    
    logger.debug(
        f"审计日志: {action} {method} {path} -> {status_code}",
        extra={
            "audit_action": action,
            "tenant_id": tenant_id,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
    )
    
    return log


async def query_audit_logs(
    session: AsyncSession,
    *,
    tenant_id: str | None = None,
    api_key_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    status_code: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """
    查询审计日志
    
    Args:
        session: 数据库会话
        tenant_id: 按租户过滤
        api_key_id: 按 API Key 过滤
        action: 按操作类型过滤
        resource_type: 按资源类型过滤
        status_code: 按状态码过滤
        start_time: 起始时间
        end_time: 结束时间
        limit: 返回数量限制
        offset: 偏移量
    
    Returns:
        审计日志列表
    """
    conditions = []
    
    if tenant_id:
        conditions.append(AuditLog.tenant_id == tenant_id)
    if api_key_id:
        conditions.append(AuditLog.api_key_id == api_key_id)
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if status_code:
        conditions.append(AuditLog.status_code == status_code)
    if start_time:
        conditions.append(AuditLog.created_at >= start_time)
    if end_time:
        conditions.append(AuditLog.created_at <= end_time)
    
    query = (
        select(AuditLog)
        .where(and_(*conditions) if conditions else True)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
        .offset(offset)
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_audit_stats(
    session: AsyncSession,
    *,
    tenant_id: str | None = None,
    hours: int = 24,
) -> dict[str, Any]:
    """
    获取审计统计信息
    
    Args:
        session: 数据库会话
        tenant_id: 按租户过滤
        hours: 统计时间范围（小时）
    
    Returns:
        统计信息字典
    """
    from sqlalchemy import func
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    conditions = [AuditLog.created_at >= start_time]
    if tenant_id:
        conditions.append(AuditLog.tenant_id == tenant_id)
    
    # 总请求数
    total_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    total_result = await session.execute(total_query)
    total_count = total_result.scalar() or 0
    
    # 按操作类型统计
    action_query = (
        select(AuditLog.action, func.count(AuditLog.id))
        .where(and_(*conditions))
        .group_by(AuditLog.action)
    )
    action_result = await session.execute(action_query)
    action_stats = dict(action_result.all())
    
    # 错误请求数
    error_conditions = conditions + [AuditLog.status_code >= 400]
    error_query = select(func.count(AuditLog.id)).where(and_(*error_conditions))
    error_result = await session.execute(error_query)
    error_count = error_result.scalar() or 0
    
    # 平均响应时间
    avg_query = select(func.avg(AuditLog.duration_ms)).where(and_(*conditions))
    avg_result = await session.execute(avg_query)
    avg_duration = avg_result.scalar() or 0
    
    return {
        "period_hours": hours,
        "total_requests": total_count,
        "error_requests": error_count,
        "error_rate": error_count / total_count if total_count > 0 else 0,
        "avg_duration_ms": round(avg_duration, 2),
        "by_action": action_stats,
    }
