"""
模型配置解析服务 (Model Config Resolver)

按优先级合并模型配置：请求级 > 知识库级 > 租户级 > 系统级 > 环境变量默认

配置层级说明：
- 环境变量：最低优先级，用于设置系统默认值
- 系统配置表（SystemConfig）：可通过 Admin API 动态修改
- 租户配置（Tenant.llm_settings）：租户专属配置
- 知识库配置（KnowledgeBase.config）：仅用于 Embedding（创建时固定）
- 请求级覆盖：API 请求中临时指定

使用示例：
    from app.services.model_config import model_config_resolver
    
    # 获取 LLM 配置
    config = await model_config_resolver.get_llm_config(session, tenant=tenant)
    
    # 获取 Embedding 配置（从 KB）
    config = await model_config_resolver.get_embedding_config(session, kb=kb)
"""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import KnowledgeBase, SystemConfig, Tenant

logger = logging.getLogger(__name__)


class ModelConfigResolver:
    """
    模型配置解析器
    
    按优先级合并配置，支持多层级覆盖。
    """
    
    # 支持的配置键
    LLM_KEYS = ["llm_provider", "llm_model", "llm_temperature", "llm_max_tokens"]
    EMBEDDING_KEYS = ["embedding_provider", "embedding_model", "embedding_dim"]
    RERANK_KEYS = ["rerank_provider", "rerank_model", "rerank_top_k"]
    
    async def _get_system_config(self, session: AsyncSession, key: str) -> str | None:
        """从数据库获取系统配置"""
        result = await session.execute(
            select(SystemConfig.value).where(SystemConfig.key == key)
        )
        row = result.scalar_one_or_none()
        return row
    
    async def _get_system_configs(self, session: AsyncSession, keys: list[str]) -> dict[str, Any]:
        """批量获取系统配置"""
        result = await session.execute(
            select(SystemConfig.key, SystemConfig.value).where(SystemConfig.key.in_(keys))
        )
        configs = {}
        for row in result:
            try:
                # 尝试 JSON 解析
                configs[row.key] = json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                configs[row.key] = row.value
        return configs
    
    def _get_env_defaults(self, keys: list[str]) -> dict[str, Any]:
        """从环境变量获取默认值"""
        settings = get_settings()
        defaults = {}
        
        key_mapping = {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "llm_temperature": settings.llm_temperature,
            "llm_max_tokens": settings.llm_max_tokens,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "embedding_dim": settings.embedding_dim,
            "rerank_provider": settings.rerank_provider,
            "rerank_model": settings.rerank_model,
            "rerank_top_k": settings.rerank_top_k,
        }
        
        for key in keys:
            if key in key_mapping:
                defaults[key] = key_mapping[key]
        
        return defaults
    
    def _merge_configs(self, *configs: dict[str, Any] | None) -> dict[str, Any]:
        """
        合并配置，后面的配置优先级更高
        
        Args:
            *configs: 按优先级从低到高排列的配置字典
        
        Returns:
            合并后的配置
        """
        result = {}
        for config in configs:
            if config:
                # 只更新非 None 的值
                for k, v in config.items():
                    if v is not None:
                        result[k] = v
        return result
    
    async def get_llm_config(
        self,
        session: AsyncSession,
        tenant: Tenant | None = None,
        request_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        获取 LLM 配置
        
        优先级：请求级 > 租户级 > 系统级 > 环境变量
        
        Args:
            session: 数据库会话
            tenant: 租户对象（可选）
            request_override: 请求级覆盖配置（可选）
        
        Returns:
            合并后的 LLM 配置字典，包含：
            - llm_provider: 提供商
            - llm_model: 模型名称
            - llm_temperature: 温度参数
            - llm_max_tokens: 最大 token 数
        """
        # 1. 环境变量默认值
        env_config = self._get_env_defaults(self.LLM_KEYS)
        
        # 2. 系统配置表
        system_config = await self._get_system_configs(session, self.LLM_KEYS)
        
        # 3. 租户配置
        tenant_config = {}
        if tenant and tenant.llm_settings:
            tenant_config = {
                k: v for k, v in tenant.llm_settings.items() 
                if k in self.LLM_KEYS
            }
        
        # 4. 请求级覆盖
        request_config = {}
        if request_override:
            request_config = {
                k: v for k, v in request_override.items() 
                if k in self.LLM_KEYS
            }
        
        # 合并配置（后面的优先级更高）
        merged = self._merge_configs(env_config, system_config, tenant_config, request_config)
        
        logger.debug(
            f"LLM config resolved: provider={merged.get('llm_provider')}, "
            f"model={merged.get('llm_model')}"
        )
        
        return merged
    
    async def get_embedding_config(
        self,
        session: AsyncSession,
        kb: KnowledgeBase | None = None,
        tenant: Tenant | None = None,
    ) -> dict[str, Any]:
        """
        获取 Embedding 配置
        
        优先级：知识库级（固定）> 系统级 > 环境变量
        
        注意：Embedding 模型通常与知识库绑定，不支持请求级覆盖。
        因为向量维度必须与知识库一致。
        
        Args:
            session: 数据库会话
            kb: 知识库对象（可选）
            tenant: 租户对象（可选，用于获取默认配置）
        
        Returns:
            合并后的 Embedding 配置字典
        """
        # 1. 环境变量默认值
        env_config = self._get_env_defaults(self.EMBEDDING_KEYS)
        
        # 2. 系统配置表
        system_config = await self._get_system_configs(session, self.EMBEDDING_KEYS)
        
        # 3. 知识库配置（最高优先级，不可覆盖）
        kb_config = {}
        if kb and kb.config and isinstance(kb.config, dict):
            embedding_cfg = kb.config.get("embedding")
            if isinstance(embedding_cfg, dict):
                provider = embedding_cfg.get("provider")
                model = embedding_cfg.get("model")
                dim = embedding_cfg.get("dim")
                if provider is not None:
                    kb_config["embedding_provider"] = provider
                if model is not None:
                    kb_config["embedding_model"] = model
                if dim is not None:
                    kb_config["embedding_dim"] = dim
            # 兼容旧版扁平字段
            for key in self.EMBEDDING_KEYS:
                if key not in kb_config and kb.config.get(key) is not None:
                    kb_config[key] = kb.config.get(key)
        
        # 合并配置
        merged = self._merge_configs(env_config, system_config, kb_config)
        
        logger.debug(
            f"Embedding config resolved: provider={merged.get('embedding_provider')}, "
            f"model={merged.get('embedding_model')}, dim={merged.get('embedding_dim')}"
        )
        
        return merged
    
    async def get_rerank_config(
        self,
        session: AsyncSession,
        tenant: Tenant | None = None,
        request_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        获取 Rerank 配置
        
        优先级：请求级 > 租户级 > 系统级 > 环境变量
        
        Args:
            session: 数据库会话
            tenant: 租户对象（可选）
            request_override: 请求级覆盖配置（可选）
        
        Returns:
            合并后的 Rerank 配置字典
        """
        # 1. 环境变量默认值
        env_config = self._get_env_defaults(self.RERANK_KEYS)
        
        # 2. 系统配置表
        system_config = await self._get_system_configs(session, self.RERANK_KEYS)
        
        # 3. 租户配置
        tenant_config = {}
        if tenant and tenant.llm_settings:
            tenant_config = {
                k: v for k, v in tenant.llm_settings.items() 
                if k in self.RERANK_KEYS
            }
        
        # 4. 请求级覆盖
        request_config = {}
        if request_override:
            request_config = {
                k: v for k, v in request_override.items() 
                if k in self.RERANK_KEYS
            }
        
        # 合并配置
        merged = self._merge_configs(env_config, system_config, tenant_config, request_config)
        
        logger.debug(
            f"Rerank config resolved: provider={merged.get('rerank_provider')}, "
            f"model={merged.get('rerank_model')}"
        )
        
        return merged
    
    async def get_full_config(
        self,
        session: AsyncSession,
        tenant: Tenant | None = None,
        kb: KnowledgeBase | None = None,
        request_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        获取完整的模型配置（LLM + Embedding + Rerank）
        
        Args:
            session: 数据库会话
            tenant: 租户对象
            kb: 知识库对象
            request_override: 请求级覆盖
        
        Returns:
            包含所有模型配置的字典
        """
        llm_config = await self.get_llm_config(session, tenant, request_override)
        embedding_config = await self.get_embedding_config(session, kb, tenant)
        rerank_config = await self.get_rerank_config(session, tenant, request_override)
        
        return {
            **llm_config,
            **embedding_config,
            **rerank_config,
        }
    
    def build_provider_config(self, config: dict[str, Any], config_type: str) -> dict[str, Any]:
        """
        构建提供商配置（用于 infra 层调用）
        
        根据 provider 类型，获取对应的 API Key 和 Base URL。
        
        Args:
            config: 模型配置字典
            config_type: 配置类型 ("llm", "embedding", "rerank")
        
        Returns:
            提供商配置字典，包含 provider, model, api_key, base_url 等
        """
        settings = get_settings()
        
        provider_key = f"{config_type}_provider"
        model_key = f"{config_type}_model"
        
        provider = config.get(provider_key)
        model = config.get(model_key)
        
        if not provider:
            raise ValueError(f"未配置 {config_type} 提供商")
        
        # 使用 Settings 的方法获取提供商配置
        return settings._get_provider_config(provider, model)


# 全局单例
model_config_resolver = ModelConfigResolver()
