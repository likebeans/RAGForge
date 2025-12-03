"""
数据模型层 (ORM Models)

这个模块定义了所有的数据库表结构，使用 SQLAlchemy ORM 映射。

数据模型关系图：
    Tenant (租户)
       │
       ├── User (用户)
       │
       ├── APIKey (API 密钥)
       │
       └── KnowledgeBase (知识库)
              │
              └── Document (文档)
                     │
                     └── Chunk (文档片段)

核心概念：
- Tenant: 租户，多租户隔离的顶层实体
- KnowledgeBase: 知识库，文档的逻辑分组
- Document: 文档，用户上传的原始文件
- Chunk: 文档片段，切分后的文本块（用于向量检索）
"""

from app.models.api_key import APIKey
from app.models.audit_log import AuditLog
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.tenant import Tenant
from app.models.usage_log import UsageLog
from app.models.user import User

# 导出所有模型，方便外部导入
__all__ = [
    "APIKey",
    "AuditLog",
    "Chunk",
    "Document",
    "KnowledgeBase",
    "Tenant",
    "UsageLog",
    "User",
]
