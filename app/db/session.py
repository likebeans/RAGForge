"""
数据库会话管理

这个模块负责：
1. 创建数据库引擎（连接池）
2. 提供异步会话工厂
3. 实现 FastAPI 依赖注入的数据库会话获取函数

核心概念：
- Engine: 数据库连接池，管理与数据库的物理连接
- Session: 数据库会话，用于执行 SQL 和管理事务
- SessionLocal: 会话工厂，用于创建新的数据库会话

使用方式（在 FastAPI 路由中）：
    from app.db.session import get_db
    
    @router.get("/users")
    async def get_users(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        return result.scalars().all()
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.base import Base

# 获取配置
settings = get_settings()

# ==================== 创建数据库引擎 ====================
# 引擎是数据库连接的入口，负责管理连接池
engine = create_async_engine(
    settings.database_url,  # 数据库连接字符串
    echo=False,             # 是否打印 SQL 语句（调试时可设为 True）
    future=True,            # 使用 SQLAlchemy 2.0 风格
    pool_pre_ping=True,     # 每次从连接池获取连接前先测试连接是否有效
                            # 这可以避免使用已断开的连接导致的错误
    # 连接池配置（生产环境优化）
    pool_size=10,           # 连接池保持的连接数
    max_overflow=20,        # 允许超出 pool_size 的额外连接数
    pool_timeout=30,        # 获取连接的超时时间（秒）
    pool_recycle=1800,      # 连接回收时间（秒），防止数据库端超时断开
)

# ==================== 创建会话工厂 ====================
# 会话工厂用于创建数据库会话，每个请求应该使用独立的会话
SessionLocal = async_sessionmaker(
    engine,                  # 绑定到上面创建的引擎
    expire_on_commit=False,  # 提交后不自动过期对象
                             # 这样可以在提交后继续访问对象属性
                             # 而不会触发额外的数据库查询
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（FastAPI 依赖注入函数）
    
    这是一个异步生成器函数，用于 FastAPI 的依赖注入系统。
    它会：
    1. 为每个请求创建一个新的数据库会话
    2. 在请求处理完成后自动关闭会话
    
    使用 async with 确保会话在使用完毕后正确关闭，
    即使发生异常也能保证资源释放。
    
    Yields:
        AsyncSession: 异步数据库会话对象
    """
    async with SessionLocal() as session:
        yield session
        # 会话在这里自动关闭（async with 的 __aexit__）


async def init_models() -> None:
    """
    初始化数据库表（仅开发环境使用）
    
    这个函数会根据所有 ORM 模型自动创建对应的数据库表。
    
    警告：
        - 这个方法仅适用于开发环境快速启动
        - 生产环境应该使用 Alembic 进行数据库迁移
        - 此方法不会修改已存在的表结构
    
    工作原理：
        1. 导入所有模型模块，让 SQLAlchemy 收集表定义
        2. 通过 Base.metadata.create_all() 创建所有表
    """
    # 导入 models 包，触发所有模型的注册
    # noqa: F401 告诉 linter 忽略"导入但未使用"的警告
    from app import models  # noqa: F401

    # 在一个事务中创建所有表
    async with engine.begin() as conn:
        # run_sync 允许在异步上下文中运行同步函数
        # create_all 是同步函数，需要这样包装
        await conn.run_sync(Base.metadata.create_all)
