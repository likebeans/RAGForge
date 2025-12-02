"""
数据库模块

这个模块负责数据库相关的所有底层操作：
- base.py    : SQLAlchemy 基类定义，所有 ORM 模型都继承自它
- session.py : 数据库会话管理（连接池、异步会话工厂）

使用 SQLAlchemy 2.0 + asyncpg 实现完全异步的数据库操作。

典型使用方式：
    from app.db.session import get_db
    
    async def my_endpoint(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        users = result.scalars().all()
"""
