"""
系统配置模型 (SystemConfig)

存储系统级配置，支持通过 Admin API 动态修改，无需重启服务。

主要用途：
- 存储默认 LLM/Embedding/Rerank 模型配置
- 支持运行时动态调整
- 环境变量作为默认值，数据库配置优先级更高

配置优先级：请求级 > 知识库级 > 租户级 > 系统级(本表) > 环境变量默认
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemConfig(Base):
    """
    系统配置表
    
    存储全局配置项，可通过 Admin API 动态修改。
    
    字段说明：
    - key: 配置键名，主键
    - value: 配置值，JSON 字符串格式
    - description: 配置描述
    - updated_at: 最后更新时间
    
    预置配置项：
    - llm_provider: 默认 LLM 提供商
    - llm_model: 默认 LLM 模型
    - llm_temperature: 默认温度参数
    - llm_max_tokens: 默认最大 token 数
    - embedding_provider: 默认 Embedding 提供商
    - embedding_model: 默认 Embedding 模型
    - embedding_dim: 默认向量维度
    - rerank_provider: 默认 Rerank 提供商
    - rerank_model: 默认 Rerank 模型
    - rerank_top_k: 默认 Rerank 返回数量
    """
    __tablename__ = "system_configs"
    
    # 配置键名（主键）
    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    
    # 配置值（JSON 字符串）
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # 配置描述
    description: Mapped[str | None] = mapped_column(
        String(500),
    )
    
    # 最后更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# 预置配置项定义
DEFAULT_SYSTEM_CONFIGS = {
    # LLM 配置
    "llm_provider": {
        "description": "默认 LLM 提供商 (ollama/openai/gemini/qwen/kimi/deepseek/zhipu/siliconflow)",
        "env_key": "LLM_PROVIDER",
    },
    "llm_model": {
        "description": "默认 LLM 模型名称",
        "env_key": "LLM_MODEL",
    },
    "llm_temperature": {
        "description": "默认 LLM 温度参数 (0-2)",
        "env_key": "LLM_TEMPERATURE",
    },
    "llm_max_tokens": {
        "description": "默认 LLM 最大生成 token 数",
        "env_key": "LLM_MAX_TOKENS",
    },
    
    # Embedding 配置
    "embedding_provider": {
        "description": "默认 Embedding 提供商 (ollama/openai/gemini/qwen/zhipu/siliconflow)",
        "env_key": "EMBEDDING_PROVIDER",
    },
    "embedding_model": {
        "description": "默认 Embedding 模型名称",
        "env_key": "EMBEDDING_MODEL",
    },
    "embedding_dim": {
        "description": "默认向量维度",
        "env_key": "EMBEDDING_DIM",
    },
    
    # Rerank 配置
    "rerank_provider": {
        "description": "默认 Rerank 提供商 (ollama/cohere/zhipu/siliconflow/none)",
        "env_key": "RERANK_PROVIDER",
    },
    "rerank_model": {
        "description": "默认 Rerank 模型名称",
        "env_key": "RERANK_MODEL",
    },
    "rerank_top_k": {
        "description": "默认 Rerank 返回数量",
        "env_key": "RERANK_TOP_K",
    },
}
