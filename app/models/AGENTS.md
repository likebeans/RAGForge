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
| `tenant.py` | 租户模型（含状态、配额管理） |
| `user.py` | 用户模型 |
| `api_key.py` | API Key 模型（含角色、作用域） |
| `knowledge_base.py` | 知识库模型 |
| `document.py` | 文档模型 |
| `chunk.py` | 文档片段模型 |
| `usage_log.py` | 用量日志模型 |

## 数据模型关系

```
Tenant (租户)
├── status              # active/disabled/pending
├── quota_kb_count      # 知识库配额
├── quota_doc_count     # 文档配额
├── quota_storage_mb    # 存储配额
├── disabled_at/reason  # 禁用信息
├── User (用户)
├── ApiKey (API 密钥)
│   ├── role            # admin/write/read
│   ├── scope_kb_ids    # KB 访问白名单
│   └── is_initial      # 初始管理员 Key
├── UsageLog (用量日志)
└── KnowledgeBase (知识库)
    └── Document (文档)
        │   ├── summary            # 文档摘要
        │   └── summary_status     # 摘要生成状态
        └── Chunk (片段)
            ├── enriched_text      # 增强后的文本（可选）
            └── enrichment_status  # 增强状态
```

## Tenant 模型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | String(20) | 状态: active/disabled/pending |
| `quota_kb_count` | Integer | 知识库数量限制，-1=无限 |
| `quota_doc_count` | Integer | 文档数量限制，-1=无限 |
| `quota_storage_mb` | Integer | 存储限制(MB)，-1=无限 |
| `disabled_at` | DateTime | 禁用时间 |
| `disabled_reason` | Text | 禁用原因 |

## APIKey 模型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | String(20) | 角色: admin/write/read |
| `scope_kb_ids` | JSON | KB 白名单，null=全部 |
| `is_initial` | Boolean | 是否为初始管理员 Key |
| `description` | Text | 描述/备注 |

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
