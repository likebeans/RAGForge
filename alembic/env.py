"""
Alembic 迁移环境配置

负责配置数据库迁移的运行环境，支持：
- 离线模式：生成 SQL 脚本
- 在线模式：直接执行迁移

注意事项：
- 导入 app.models 确保所有模型被注册
- 支持异步数据库连接（asyncpg）
- 数据库 URL 优先从环境变量读取
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.db.base import Base
from app import models  # noqa: F401 - 确保所有模型被导入和注册

# Alembic 配置对象，提供对 .ini 配置文件的访问
config = context.config

# 配置 Python 日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据：包含所有模型的表结构定义
target_metadata = Base.metadata


def get_url() -> str:
    """获取数据库连接 URL，优先使用环境变量"""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    settings = get_settings()
    return settings.database_url


def run_migrations_offline() -> None:
    """
    离线模式运行迁移
    
    不实际连接数据库，仅生成 SQL 脚本。
    适用于需要审核 SQL 或手动执行的场景。
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """执行迁移操作（同步函数，被 run_sync 调用）"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移
    
    连接到实际数据库执行迁移。
    使用异步引擎支持 asyncpg 驱动。
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    # 创建异步数据库引擎
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 禁用连接池，迁移完成后立即释放
    )

    async def async_run_migrations():
        """异步执行迁移"""
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    import asyncio

    asyncio.run(async_run_migrations())


# 根据模式选择运行方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
