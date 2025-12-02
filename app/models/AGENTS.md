# Models ORM 模型模块

SQLAlchemy ORM 模型定义。

## 模块职责

- 定义数据库表结构
- 定义模型关系（外键、关联）
- 提供通用 Mixin（时间戳、软删除等）

## 核心文件

| 文件 | 说明 |
|------|------|
| `mixins.py` | 通用 Mixin（TimestampMixin, SoftDeleteMixin） |
| `tenant.py` | 租户模型 |
| `user.py` | 用户模型 |
| `api_key.py` | API Key 模型 |
| `knowledge_base.py` | 知识库模型 |
| `document.py` | 文档模型 |
| `chunk.py` | 文档片段模型 |

## 数据模型关系

```
Tenant (租户)
├── User (用户)
├── ApiKey (API 密钥)
└── KnowledgeBase (知识库)
    └── Document (文档)
        │   ├── summary            # 文档摘要
        │   └── summary_status     # 摘要生成状态
        └── Chunk (片段)
            ├── enriched_text      # 增强后的文本（可选）
            └── enrichment_status  # 增强状态
```

## 模型示例

```python
from app.db.base import Base
from app.models.mixins import TimestampMixin

class MyModel(Base, TimestampMixin):
    __tablename__ = "my_table"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    
    # 避免使用 metadata 字段名，使用 extra_metadata
    extra_metadata = Column("metadata", JSON, default=dict)
```

## Mixin 说明

### TimestampMixin
- `created_at`: 创建时间
- `updated_at`: 更新时间（自动更新）

### SoftDeleteMixin
- `deleted_at`: 软删除时间
- `is_deleted`: 是否已删除

## 多租户设计

所有业务模型都包含 `tenant_id` 字段：
- 查询时必须过滤 `tenant_id`
- 外键约束确保数据隔离
- 级联删除防止孤立数据

## 添加新模型

1. 创建模型文件 `app/models/my_model.py`
2. 在 `__init__.py` 中导出
3. 创建迁移：`uv run alembic revision --autogenerate -m "add my_model"`
4. 执行迁移：`uv run alembic upgrade head`

## 注意事项

- 避免使用 `metadata` 作为字段名（SQLAlchemy 保留字）
- 使用 `extra_metadata` 并显式指定列名 `Column("metadata", ...)`
- 主键推荐使用 UUID 字符串
- 时间字段使用 `DateTime(timezone=True)`
