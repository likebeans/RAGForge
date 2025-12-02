# DB 数据库模块

SQLAlchemy 异步数据库配置和会话管理。

## 模块职责

- 配置异步数据库引擎
- 管理数据库会话生命周期
- 定义 ORM 基类

## 核心文件

| 文件 | 说明 |
|------|------|
| `base.py` | SQLAlchemy Base 类定义 |
| `session.py` | 异步引擎和会话工厂 |

## 连接配置

```python
# 环境变量
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname

# 本地开发
DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 容器内
DATABASE_URL=postgresql+asyncpg://kb:kb@db:5432/kb
```

## 会话使用

### 在路由中（推荐）
```python
from app.api.deps import get_db

@router.get("/")
async def handler(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model))
    return result.scalars().all()
```

### 在服务层
```python
from app.db.session import async_session_maker

async def my_service():
    async with async_session_maker() as session:
        # 使用 session
        await session.commit()
```

## ORM 基类

```python
from app.db.base import Base

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(String(36), primary_key=True)
    # ...
```

## 注意事项

- 使用 `asyncpg` 驱动，所有操作需要 `await`
- 避免使用 `metadata` 作为字段名（SQLAlchemy 保留字）
- 会话在请求结束后自动关闭
- 事务需要显式 `commit()`
