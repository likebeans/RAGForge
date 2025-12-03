"""
BM25 全局缓存管理器

提供跨请求的 chunks 缓存，避免每次检索都从数据库加载。
支持 TTL 过期和手动失效。
"""

import asyncio
import time
from typing import Any


class BM25ChunkCache:
    """
    BM25 chunks 全局缓存
    
    特点：
    - 进程级单例，跨请求共享
    - TTL 自动过期
    - 支持按 KB 失效（文档更新时调用）
    """
    
    def __init__(self, default_ttl: int = 60, max_entries: int = 100):
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._cache: dict[tuple, tuple[float, list[dict]]] = {}  # key -> (expire_time, chunks)
        self._lock = asyncio.Lock()
    
    async def get(self, tenant_id: str, kb_ids: list[str]) -> list[dict] | None:
        """获取缓存的 chunks，如果过期或不存在返回 None"""
        key = (tenant_id, tuple(sorted(kb_ids)))
        entry = self._cache.get(key)
        if entry is None:
            return None
        expire_time, chunks = entry
        if time.time() > expire_time:
            # 过期，删除并返回 None
            self._cache.pop(key, None)
            return None
        return chunks
    
    async def set(self, tenant_id: str, kb_ids: list[str], chunks: list[dict], ttl: int | None = None) -> None:
        """设置缓存"""
        key = (tenant_id, tuple(sorted(kb_ids)))
        expire_time = time.time() + (ttl or self.default_ttl)
        
        async with self._lock:
            # 如果缓存满了，删除最旧的条目
            if len(self._cache) >= self.max_entries and key not in self._cache:
                self._evict_oldest()
            self._cache[key] = (expire_time, chunks)
    
    async def invalidate(self, tenant_id: str, kb_id: str | None = None) -> int:
        """
        失效缓存
        
        Args:
            tenant_id: 租户 ID
            kb_id: 知识库 ID，如果为 None 则失效该租户所有缓存
        
        Returns:
            删除的缓存条目数
        """
        async with self._lock:
            keys_to_delete = []
            for key in self._cache:
                t_id, kb_tuple = key
                if t_id != tenant_id:
                    continue
                if kb_id is None or kb_id in kb_tuple:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self._cache.pop(key, None)
            return len(keys_to_delete)
    
    def _evict_oldest(self) -> None:
        """删除最早过期的条目"""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
        self._cache.pop(oldest_key, None)
    
    def stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        now = time.time()
        valid_count = sum(1 for _, (exp, _) in self._cache.items() if exp > now)
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "expired_entries": len(self._cache) - valid_count,
            "max_entries": self.max_entries,
            "default_ttl": self.default_ttl,
        }


# 全局单例
_global_cache: BM25ChunkCache | None = None


def get_bm25_cache(ttl: int = 60, max_entries: int = 100) -> BM25ChunkCache:
    """获取全局 BM25 缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = BM25ChunkCache(default_ttl=ttl, max_entries=max_entries)
    return _global_cache
