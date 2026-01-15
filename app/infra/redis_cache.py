"""
Redis 缓存模块

提供查询结果缓存和配置缓存功能，减少数据库查询和 LLM 调用。

缓存策略：
- 查询缓存：基于 (tenant_id, query, kb_ids, retriever_name, top_k) 生成缓存键
- 配置缓存：基于 (tenant_id, kb_id) 生成缓存键
- 使用 TTL 自动过期，避免缓存污染
"""

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis 缓存客户端
    
    提供查询缓存和配置缓存功能。
    如果 Redis 不可用，自动降级为无缓存模式（不影响业务逻辑）。
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._available = False
        self._init_client()
    
    def _init_client(self) -> None:
        """初始化 Redis 客户端"""
        if not self.settings.redis_url:
            logger.info("Redis 未配置，缓存功能已禁用")
            return
        
        if not self.settings.redis_cache_enabled:
            logger.info("Redis 缓存已禁用（redis_cache_enabled=False）")
            return
        
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            self._available = True
            logger.info(f"Redis 缓存已启用: {self.settings.redis_url}")
        except ImportError:
            logger.warning("redis 模块未安装，缓存功能已禁用。请运行: pip install redis")
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}，缓存功能已禁用")
    
    @property
    def available(self) -> bool:
        """Redis 是否可用"""
        return self._available
    
    def _make_cache_key(self, prefix: str, **kwargs: Any) -> str:
        """
        生成缓存键
        
        基于参数生成 MD5 哈希，确保键长度固定且唯一。
        
        Args:
            prefix: 键前缀
            **kwargs: 用于生成键的参数
            
        Returns:
            str: 缓存键，格式为 {prefix}{hash}
        """
        # 排序参数确保键稳定
        sorted_params = json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{self.settings.redis_cache_key_prefix}{prefix}{hash_value}"
    
    async def get_query_cache(
        self,
        *,
        tenant_id: str,
        query: str,
        kb_ids: list[str],
        retriever_name: str,
        top_k: int,
    ) -> dict | None:
        """
        获取查询缓存
        
        Args:
            tenant_id: 租户 ID
            query: 查询文本
            kb_ids: 知识库 ID 列表
            retriever_name: 检索器名称
            top_k: 返回结果数量
            
        Returns:
            dict | None: 缓存的查询结果，不存在或已过期则返回 None
        """
        if not self.available:
            return None
        
        try:
            key = self._make_cache_key(
                "query:",
                tenant_id=tenant_id,
                query=query,
                kb_ids=sorted(kb_ids),  # 排序确保键稳定
                retriever_name=retriever_name,
                top_k=top_k,
            )
            
            cached = await self._client.get(key)
            if cached:
                logger.debug(f"查询缓存命中: key={key[:50]}...")
                return json.loads(cached)
            
            return None
        except Exception as e:
            logger.warning(f"获取查询缓存失败: {e}")
            return None
    
    async def set_query_cache(
        self,
        *,
        tenant_id: str,
        query: str,
        kb_ids: list[str],
        retriever_name: str,
        top_k: int,
        result: dict,
    ) -> None:
        """
        设置查询缓存
        
        Args:
            tenant_id: 租户 ID
            query: 查询文本
            kb_ids: 知识库 ID 列表
            retriever_name: 检索器名称
            top_k: 返回结果数量
            result: 查询结果（会被序列化为 JSON）
        """
        if not self.available:
            return
        
        try:
            key = self._make_cache_key(
                "query:",
                tenant_id=tenant_id,
                query=query,
                kb_ids=sorted(kb_ids),
                retriever_name=retriever_name,
                top_k=top_k,
            )
            
            await self._client.setex(
                key,
                self.settings.redis_cache_ttl,
                json.dumps(result, ensure_ascii=False),
            )
            logger.debug(f"查询缓存已保存: key={key[:50]}...")
        except Exception as e:
            logger.warning(f"设置查询缓存失败: {e}")
    
    async def invalidate_kb_cache(
        self,
        *,
        tenant_id: str,
        kb_id: str,
    ) -> None:
        """
        失效知识库相关缓存（在文档入库/删除时调用）
        
        注意：由于无法精确匹配所有包含该 KB 的查询缓存，
        这里只失效配置缓存。查询缓存会自然过期（TTL）。
        
        Args:
            tenant_id: 租户 ID
            kb_id: 知识库 ID
        """
        if not self.available:
            return
        
        try:
            # 失效配置缓存
            config_key = self._make_cache_key(
                "config:",
                tenant_id=tenant_id,
                kb_id=kb_id,
            )
            await self._client.delete(config_key)
            logger.debug(f"知识库配置缓存已失效: kb_id={kb_id}")
        except Exception as e:
            logger.warning(f"失效知识库缓存失败: {e}")
    
    async def get_kb_config_cache(
        self,
        *,
        tenant_id: str,
        kb_id: str,
    ) -> dict | None:
        """
        获取知识库配置缓存
        
        Args:
            tenant_id: 租户 ID
            kb_id: 知识库 ID
            
        Returns:
            dict | None: 缓存的配置，不存在或已过期则返回 None
        """
        if not self.available:
            return None
        
        try:
            key = self._make_cache_key(
                "config:",
                tenant_id=tenant_id,
                kb_id=kb_id,
            )
            
            cached = await self._client.get(key)
            if cached:
                logger.debug(f"配置缓存命中: kb_id={kb_id}")
                return json.loads(cached)
            
            return None
        except Exception as e:
            logger.warning(f"获取配置缓存失败: {e}")
            return None
    
    async def set_kb_config_cache(
        self,
        *,
        tenant_id: str,
        kb_id: str,
        config: dict,
    ) -> None:
        """
        设置知识库配置缓存
        
        Args:
            tenant_id: 租户 ID
            kb_id: 知识库 ID
            config: 配置对象（会被序列化为 JSON）
        """
        if not self.available:
            return
        
        try:
            key = self._make_cache_key(
                "config:",
                tenant_id=tenant_id,
                kb_id=kb_id,
            )
            
            await self._client.setex(
                key,
                self.settings.redis_config_cache_ttl,
                json.dumps(config, ensure_ascii=False),
            )
            logger.debug(f"配置缓存已保存: kb_id={kb_id}")
        except Exception as e:
            logger.warning(f"设置配置缓存失败: {e}")
    
    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            logger.info("Redis 连接已关闭")


@lru_cache(maxsize=1)
def get_redis_cache() -> RedisCache:
    """
    获取 Redis 缓存单例
    
    使用 lru_cache 确保全局只有一个实例。
    
    Returns:
        RedisCache: Redis 缓存客户端
    """
    return RedisCache()
