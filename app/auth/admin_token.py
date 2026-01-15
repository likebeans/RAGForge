"""
管理员 Token 认证模块

提供管理员 Token 的生成、验证和管理功能。

安全设计：
- Token 使用 SHA256 哈希存储
- 支持多个管理员 Token
- 支持过期时间和撤销
- 记录使用情况
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models import AdminToken

logger = logging.getLogger(__name__)


def hash_admin_token(raw_token: str) -> str:
    """对管理员 Token 进行 SHA256 哈希"""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_admin_token(prefix: str = "admin_") -> tuple[str, str, str]:
    """
    生成新的管理员 Token
    
    Returns:
        tuple: (完整Token用于显示, 哈希值用于存储, 前缀用于快速查找)
    """
    body = secrets.token_urlsafe(32)
    display_token = f"{prefix}{body}"
    return display_token, hash_admin_token(display_token), display_token[:12]


async def verify_admin_token_from_db(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    从数据库验证管理员 Token
    
    Args:
        x_admin_token: 请求头中的 Token
        db: 数据库会话
    
    Returns:
        str: 验证通过的 Token ID
    
    Raises:
        HTTPException: Token 无效、已撤销、已过期
    """
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_ADMIN_TOKEN", "detail": "Missing X-Admin-Token header"},
        )
    
    # 哈希 Token 并查询数据库
    hashed = hash_admin_token(x_admin_token)
    now = datetime.now(timezone.utc)
    
    result = await db.execute(
        select(AdminToken).where(
            AdminToken.hashed_token == hashed,
            AdminToken.revoked.is_(False),
        )
    )
    token = result.scalar_one_or_none()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INVALID_ADMIN_TOKEN", "detail": "Invalid or revoked admin token"},
        )
    
    # 检查过期时间
    if token.expires_at and token.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_TOKEN_EXPIRED", "detail": "Admin token has expired"},
        )
    
    # 更新最后使用时间
    token.last_used_at = now
    db.add(token)
    await db.commit()
    
    return token.id


async def verify_admin_token_legacy(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> str:
    """
    兼容旧版：从环境变量验证管理员 Token（明文比对）
    
    如果数据库中没有管理员 Token，则回退到环境变量验证。
    这是为了向后兼容，建议迁移到数据库存储。
    """
    settings = get_settings()
    
    if not settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ADMIN_API_NOT_CONFIGURED", "detail": "Admin API is not configured. Set ADMIN_TOKEN or create admin tokens in database."},
        )
    
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_ADMIN_TOKEN", "detail": "Missing X-Admin-Token header"},
        )
    
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INVALID_ADMIN_TOKEN", "detail": "Invalid admin token"},
        )
    
    return x_admin_token


async def verify_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    验证管理员 Token（自动选择数据库或环境变量）
    
    优先使用数据库验证，如果数据库中没有 Token，则回退到环境变量。
    """
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_ADMIN_TOKEN", "detail": "Missing X-Admin-Token header"},
        )
    
    # 尝试数据库验证
    try:
        hashed = hash_admin_token(x_admin_token)
        result = await db.execute(
            select(AdminToken).where(
                AdminToken.hashed_token == hashed,
                AdminToken.revoked.is_(False),
            )
        )
        token = result.scalar_one_or_none()
        
        if token:
            # 数据库中找到 Token，使用数据库验证
            now = datetime.now(timezone.utc)
            if token.expires_at and token.expires_at < now:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "ADMIN_TOKEN_EXPIRED", "detail": "Admin token has expired"},
                )
            
            # 更新最后使用时间
            token.last_used_at = now
            db.add(token)
            await db.commit()
            
            return token.id
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"数据库验证失败，回退到环境变量: {e}")
    
    # 回退到环境变量验证（兼容旧版）
    settings = get_settings()
    if settings.admin_token and x_admin_token == settings.admin_token:
        logger.info("使用环境变量验证管理员 Token（建议迁移到数据库）")
        return "env_admin_token"
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "INVALID_ADMIN_TOKEN", "detail": "Invalid admin token"},
    )
