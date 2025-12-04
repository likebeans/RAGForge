"""
API Key 认证模块

实现 API Key 的认证流程，类似 OpenAI 的认证机制：
1. 从请求头获取 Bearer Token
2. 验证 API Key 是否有效（哈希比对）
3. 检查是否过期或被撤销
4. 检查限流
5. 返回认证上下文（包含租户信息）

安全设计：
- 使用 SHA256 哈希存储，不保存明文
- 支持滑动窗口限流（内存/Redis）
- 记录最后使用时间
"""

import hashlib
import logging
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.models import APIKey, Tenant

logger = logging.getLogger(__name__)


def hash_api_key(raw_key: str) -> str:
    """对 API Key 进行 SHA256 哈希"""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key(prefix: str) -> tuple[str, str, str]:
    """
    生成新的 API Key
    
    Returns:
        tuple: (完整Key用于显示, 哈希值用于存储, 前缀用于快速查找)
    """
    body = secrets.token_urlsafe(32)  # 生成 32 字节随机字符串
    display_key = f"{prefix}{body}"
    return display_key, hash_api_key(display_key), display_key[:8]


class BaseRateLimiter(ABC):
    """限流器基类"""
    
    @abstractmethod
    def allow(self, key: str, limit_override: int | None = None) -> bool:
        """检查请求是否允许通过"""
        pass


class MemoryRateLimiter(BaseRateLimiter):
    """
    内存滑动窗口限流器
    
    适用于单实例部署，多实例部署请使用 Redis 限流器。
    """

    def __init__(self, window_seconds: int, max_requests: int) -> None:
        self.window_seconds = window_seconds
        self.default_limit = max_requests
        self._buckets: dict[str, list[float]] = {}

    def allow(self, key: str, limit_override: int | None = None) -> bool:
        limit = limit_override or self.default_limit
        now = time.time()
        window_start = now - self.window_seconds
        bucket = self._buckets.setdefault(key, [])
        
        while bucket and bucket[0] < window_start:
            bucket.pop(0)
        
        if len(bucket) >= limit:
            return False
        
        bucket.append(now)
        return True


class RedisRateLimiter(BaseRateLimiter):
    """
    Redis 滑动窗口限流器
    
    使用 Redis Sorted Set 实现，支持多实例部署。
    """

    def __init__(self, redis_url: str, window_seconds: int, max_requests: int) -> None:
        self.window_seconds = window_seconds
        self.default_limit = max_requests
        self._redis = None
        self._redis_url = redis_url
    
    @property
    def redis(self):
        if self._redis is None:
            import redis
            self._redis = redis.from_url(self._redis_url)
        return self._redis

    def allow(self, key: str, limit_override: int | None = None) -> bool:
        limit = limit_override or self.default_limit
        now = time.time()
        window_start = now - self.window_seconds
        redis_key = f"ratelimit:{key}"
        
        pipe = self.redis.pipeline()
        try:
            # 移除窗口外的时间戳
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # 获取当前窗口内的请求数
            pipe.zcard(redis_key)
            # 添加当前请求
            pipe.zadd(redis_key, {str(now): now})
            # 设置过期时间
            pipe.expire(redis_key, self.window_seconds + 1)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= limit:
                # 超限，移除刚添加的
                self.redis.zrem(redis_key, str(now))
                return False
            
            return True
        except Exception as e:
            logger.warning(f"Redis 限流异常，降级到允许通过: {e}")
            return True


@lru_cache(maxsize=1)
def get_rate_limiter() -> BaseRateLimiter:
    """获取限流器实例（单例）"""
    settings = get_settings()
    
    if settings.redis_url:
        logger.info("使用 Redis 限流器")
        return RedisRateLimiter(
            redis_url=settings.redis_url,
            window_seconds=settings.api_rate_limit_window_seconds,
            max_requests=settings.api_rate_limit_per_minute,
        )
    else:
        logger.info("使用内存限流器（单实例模式）")
        return MemoryRateLimiter(
            window_seconds=settings.api_rate_limit_window_seconds,
            max_requests=settings.api_rate_limit_per_minute,
        )


# 兼容旧代码
class SlidingWindowRateLimiter(MemoryRateLimiter):
    """【已废弃】使用 get_rate_limiter() 替代"""
    pass


rate_limiter = get_rate_limiter()


def _parse_authorization_header(header_val: str | None) -> str:
    if not header_val or not header_val.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "detail": "Missing or invalid Authorization header"},
        )
    return header_val.split(" ", 1)[1].strip()


@dataclass
class APIKeyContext:
    api_key: APIKey
    tenant: Tenant
    
    def get_user_context(self):
        """
        从 API Key 的 identity 字段生成 UserContext
        
        用于 Security Trimming 文档过滤。如果 API Key 没有 identity 字段，
        则生成一个最低权限的 UserContext（只能访问 public 文档）。
        
        Returns:
            UserContext: 用户上下文对象
        """
        from app.services.acl import UserContext
        
        identity = self.api_key.identity or {}
        return UserContext(
            user_id=identity.get("user_id"),
            roles=identity.get("roles"),
            groups=identity.get("groups"),
            sensitivity_clearance=identity.get("clearance", "public"),
            is_admin=(self.api_key.role == "admin"),
        )


async def get_api_key_context(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> APIKeyContext:
    raw_key = _parse_authorization_header(authorization)
    hashed = hash_api_key(raw_key)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(APIKey, Tenant)
        .join(Tenant, Tenant.id == APIKey.tenant_id)
        .where(
            and_(
                APIKey.hashed_key == hashed,
                APIKey.revoked.is_(False),
                (APIKey.expires_at.is_(None)) | (APIKey.expires_at > now),
            )
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "detail": "Invalid API key"},
        )

    api_key, tenant = row

    # 检查租户状态
    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "TENANT_DISABLED", "detail": f"Tenant is {tenant.status}"},
        )

    limit_allowed = rate_limiter.allow(
        key=api_key.id,
        limit_override=api_key.rate_limit_per_minute,
    )
    if not limit_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "detail": "Rate limit exceeded"},
        )

    api_key.last_used_at = now
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyContext(api_key=api_key, tenant=tenant)
