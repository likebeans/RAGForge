"""
Yaoyan 数据库会话管理

用于连接 yaoyan 项目的数据库，执行项目数据的增删改查。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

# Yaoyan 数据库引擎
yaoyan_engine = create_async_engine(
    settings.yaoyan_database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Yaoyan 会话工厂
YaoyanSessionLocal = async_sessionmaker(
    yaoyan_engine,
    expire_on_commit=False,
)


async def get_yaoyan_db() -> AsyncGenerator[AsyncSession, None]:
    """获取 Yaoyan 数据库会话"""
    async with YaoyanSessionLocal() as session:
        yield session
