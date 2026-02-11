"""
模型配置数据库模型

存储租户级的模型配置（Embedding/LLM/Rerank），支持用户配置自己的模型 API Key。
"""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TenantModelConfig(Base, TimestampMixin):
    """
    租户级模型配置

    存储租户的模型配置（Embedding/LLM/Rerank），用户可以配置自己的模型 API Key。
    配置优先级：数据库配置 > 环境变量（fallback）
    """
    __tablename__ = "tenant_model_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 配置类型: embedding/llm/rerank
    config_type = Column(String(20), nullable=False, index=True)

    # 模型提供商: openai/ollama/siliconflow/qwen/deepseek/zhipu/cohere
    provider = Column(String(50), nullable=False)

    # 模型名称 (可选，某些场景可能只需要 provider)
    model = Column(String(100), nullable=True)

    # API Key (加密存储，使用系统密钥加密)
    api_key = Column(Text, nullable=True)

    # API Base URL (可选，用于自托管服务如 Ollama)
    base_url = Column(String(500), nullable=True)

    # 启用状态
    is_active = Column(Boolean, default=True)

    # 关联关系
    tenant = relationship("Tenant", back_populates="model_configs")

    def __repr__(self) -> str:
        return (
            f"<TenantModelConfig(id={self.id}, tenant_id={self.tenant_id}, "
            f"config_type={self.config_type}, provider={self.provider}, model={self.model})>"
        )

