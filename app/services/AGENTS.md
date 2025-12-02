# Services 业务逻辑模块

核心业务逻辑实现。

## 模块职责

- 文档摄取（切分、向量化、存储）
- 知识库检索
- 配置校验
- 复杂业务流程编排

## 核心文件

| 文件 | 说明 |
|------|------|
| `ingestion.py` | 文档摄取服务 |
| `query.py` | 检索服务 |
| `config_validation.py` | 知识库配置校验 |

## 文档摄取流程

```
上传文档 → 解析内容 → 切分片段 → 向量化 → 存储到向量库 → 保存元数据到 DB
         ↓                    ↓
    生成文档摘要（可选）    Chunk Enrichment（可选）
```

```python
from app.services.ingestion import ingest_document

# 摄取文档
chunks = await ingest_document(
    db=db,
    tenant_id=tenant.id,
    kb_id=kb.id,
    document_id=doc.id,
    content=text_content,
    chunker_name="sliding_window",
    chunker_params={"window": 512, "overlap": 50}
)
```

## 检索流程

```
查询 → 选择检索器 → 执行检索 → 过滤结果 → 返回
```

```python
from app.services.query import query_knowledge_bases

# 检索
results = await query_knowledge_bases(
    db=db,
    tenant_id=tenant.id,
    kb_ids=["kb1", "kb2"],
    query="问题内容",
    retriever_name="hybrid",
    retriever_params={"dense_weight": 0.7},
    top_k=10
)
```

## 配置校验

```python
from app.services.config_validation import validate_kb_config

# 校验知识库配置
errors = validate_kb_config({
    "chunker": "sliding_window",
    "chunker_params": {"window": 512},
    "retriever": "hybrid",
})
if errors:
    raise ValueError(errors)
```

## 服务层设计原则

1. **单一职责**：每个函数只做一件事
2. **依赖注入**：数据库会话通过参数传入
3. **事务管理**：由调用方控制 commit
4. **错误处理**：抛出明确的异常，由路由层转换为 HTTP 错误

## 添加新服务

```python
# services/my_service.py
from sqlalchemy.ext.asyncio import AsyncSession

async def my_business_logic(
    db: AsyncSession,
    tenant_id: str,
    # 其他参数
) -> Result:
    # 1. 验证输入
    # 2. 查询/操作数据库
    # 3. 调用基础设施（向量库等）
    # 4. 返回结果
    pass
```

## 注意事项

- 服务函数应该是异步的（`async def`）
- 不要在服务层直接返回 HTTP 响应
- 复杂事务应使用 `async with db.begin():`
- 日志记录关键操作便于调试
