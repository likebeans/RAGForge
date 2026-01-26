"""
模型配置加载服务

从数据库加载租户的模型配置，支持配置优先级：
数据库配置 > 环境变量（fallback）

主要功能：
- 根据 tenant_id 加载模型配置
- 支持配置类型：embedding/llm/rerank
- 返回配置字典，包含 provider, model, api_key, base_url
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, TenantModelConfig

logger = logging.getLogger(__name__)


class ModelConfigLoader:
    """
    模型配置加载器

    从数据库加载租户的模型配置，优先级：
    1. 数据库中的配置（用户自定义）
    2. 环境变量（fallback）
    """

    def __init__(self):
        # 内存缓存：{tenant_id: {config_type: config}}
        self._cache: dict[str, dict[str, TenantModelConfig]] = {}

    async def get_embedding_config(
        self,
        tenant_id: str,
        session: AsyncSession,
    ) -> Optional[dict]:
        """
        获取 Embedding 配置

        Returns:
            配置字典：{"provider": "...", "model": "...", "api_key": "...", "base_url": "..."}
            如果没有配置，返回 None
        """
        return await self._get_config(tenant_id, "embedding", session)

    async def get_llm_config(
        self,
        tenant_id: str,
        session: AsyncSession,
    ) -> Optional[dict]:
        """
        获取 LLM 配置
        """
        return await self._get_config(tenant_id, "llm", session)

    async def get_rerank_config(
        self,
        tenant_id: str,
        session: AsyncSession,
    ) -> Optional[dict]:
        """
        获取 Rerank 配置
        """
        return await self._get_config(tenant_id, "rerank", session)

    async def _get_config(
        self,
        tenant_id: str,
        config_type: str,
        session: AsyncSession,
    ) -> Optional[dict]:
        """
        内部方法：获取指定类型的配置

        优先从缓存获取，如果没有则从数据库加载
        """
        # 1. 尝试从缓存获取
        if tenant_id in self._cache:
            tenant_cache = self._cache[tenant_id]
            if config_type in tenant_cache:
                config = tenant_cache[config_type]
                if config.is_active:
                    return self._config_to_dict(config)

        # 2. 从数据库加载
        query = select(TenantModelConfig).where(
            TenantModelConfig.tenant_id == tenant_id,
            TenantModelConfig.config_type == config_type,
            TenantModelConfig.is_active == True,
        )
        result = await session.execute(query)
        config = result.scalar_one_or_none()

        if config:
            # 更新缓存
            if tenant_id not in self._cache:
                self._cache[tenant_id] = {}
            self._cache[tenant_id][config_type] = config

            logger.debug(f"Loaded {config_type} config for tenant {tenant_id}: provider={config.provider}")
            return self._config_to_dict(config)

        logger.debug(f"No {config_type} config found for tenant {tenant_id}")
        return None

    def _config_to_dict(self, config: TenantModelConfig) -> dict:
        """将配置对象转换为字典"""
        return {
            "provider": config.provider,
            "model": config.model,
            "api_key": config.api_key,
            "base_url": config.base_url,
        }

    def invalidate_cache(self, tenant_id: str, config_type: str | None = None):
        """
        使缓存失效

        Args:
            tenant_id: 租户 ID
            config_type: 配置类型，如果为 None 则失效该租户所有配置
        """
        if tenant_id not in self._cache:
            return

        if config_type:
            self._cache[tenant_id].pop(config_type, None)
            logger.debug(f"Invalidated {config_type} cache for tenant {tenant_id}")
        else:
            del self._cache[tenant_id]
            logger.debug(f"Invalidated all config cache for tenant {tenant_id}")

    def clear_all_cache(self):
        """清空所有缓存"""
        self._cache.clear()
        logger.info("Cleared all model config cache")


# 全局单例
model_config_loader = ModelConfigLoader()


async def get_model_config_loader() -> ModelConfigLoader:
    """
    依赖注入：获取模型配置加载器
    """
    return model_config_loader

