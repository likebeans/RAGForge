"""
审计日志模型

记录所有 API 访问日志，用于安全审计和问题排查。

字段说明：
- request_id: 请求唯一标识（与 X-Request-ID 头对应）
- tenant_id: 租户 ID
- api_key_id: 使用的 API Key ID
- action: 操作类型（retrieve/ingest/rag/kb_create/...）
- resource_type: 资源类型（knowledge_base/document/chunk）
- resource_id: 资源 ID
- method: HTTP 方法
- path: 请求路径
- status_code: 响应状态码
- duration_ms: 请求耗时（毫秒）
- ip_address: 客户端 IP
- user_agent: 客户端 User-Agent
- request_body: 请求体摘要（敏感信息脱敏）
- response_summary: 响应摘要
- error_message: 错误信息（如有）
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class AuditLog(Base):
    """审计日志表"""
    
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    request_id = Column(String(36), nullable=False, index=True, comment="请求 ID")
    tenant_id = Column(String(36), nullable=True, index=True, comment="租户 ID")
    api_key_id = Column(String(36), nullable=True, index=True, comment="API Key ID")
    
    # 操作信息
    action = Column(String(50), nullable=False, index=True, comment="操作类型")
    resource_type = Column(String(50), nullable=True, comment="资源类型")
    resource_id = Column(String(36), nullable=True, comment="资源 ID")
    
    # HTTP 请求信息
    method = Column(String(10), nullable=False, comment="HTTP 方法")
    path = Column(String(500), nullable=False, comment="请求路径")
    query_params = Column(JSONB, nullable=True, comment="查询参数")
    
    # 响应信息
    status_code = Column(Integer, nullable=False, index=True, comment="状态码")
    duration_ms = Column(Float, nullable=False, comment="耗时（毫秒）")
    
    # 客户端信息
    ip_address = Column(String(45), nullable=True, comment="客户端 IP")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    
    # 详细信息（可选，用于问题排查）
    request_summary = Column(Text, nullable=True, comment="请求摘要")
    response_summary = Column(Text, nullable=True, comment="响应摘要")
    error_message = Column(Text, nullable=True, comment="错误信息")
    extra_data = Column(JSONB, nullable=True, comment="扩展数据")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 复合索引：按租户和时间查询
    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.id} {self.action} {self.status_code}>"
