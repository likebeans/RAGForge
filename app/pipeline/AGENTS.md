# Pipeline 模块

可插拔的算法框架，支持动态注册和发现切分器、检索器、查询变换等组件。

## 模块职责

- 定义算法组件的标准接口（Protocol）
- 提供全局注册表，支持按名称获取组件
- 封装多种切分、检索、查询增强策略

## 核心文件

| 文件/目录 | 说明 |
|------|------|
| `base.py` | 基础协议定义（ChunkPiece, BaseChunkerOperator, BaseRetrieverOperator） |
| `registry.py` | 算法注册表（OperatorRegistry）和装饰器（@register_operator） |
| `chunkers/` | 文本切分器实现（simple/sliding_window/recursive/markdown/code 等） |
| `retrievers/` | 检索器实现（dense/bm25/hybrid/fusion/hyde 等） |
| `query_transforms/` | 查询变换（HyDE/QueryRouter/RAGFusion） |
| `enrichers/` | 文档增强（DocumentSummarizer/ChunkEnricher） |
| `postprocessors/` | 后处理（ContextWindowExpander） |

## 使用示例

```python
from app.pipeline import operator_registry

# 获取切分器
chunker = operator_registry.get("chunker", "sliding_window")(window=512, overlap=100)
pieces = chunker.chunk("长文本内容...")

# 获取检索器
retriever = operator_registry.get("retriever", "hybrid")()
results = await retriever.retrieve(
    query="问题",
    tenant_id="tenant_xxx",
    kb_ids=["kb1", "kb2"],
    top_k=5
)
```

## 扩展指南

### 添加新切分器

1. 在 `chunkers/` 下创建新文件
2. 实现 `BaseChunkerOperator` 协议
3. 使用 `@register_operator("chunker", "名称")` 装饰器注册
4. 在 `chunkers/__init__.py` 中导入

```python
from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator

@register_operator("chunker", "my_chunker")
class MyChunker(BaseChunkerOperator):
    name = "my_chunker"
    kind = "chunker"
    
    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        # 实现切分逻辑
        return [ChunkPiece(text=text, metadata=metadata or {})]
```

### 添加新检索器

1. 在 `retrievers/` 下创建新文件
2. 实现 `BaseRetrieverOperator` 协议
3. 使用 `@register_operator("retriever", "名称")` 装饰器注册
4. 在 `retrievers/__init__.py` 中导入

```python
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator

@register_operator("retriever", "my_retriever")
class MyRetriever(BaseRetrieverOperator):
    name = "my_retriever"
    kind = "retriever"
    
    async def retrieve(self, *, query: str, tenant_id: str, kb_ids: list[str], top_k: int):
        # 实现检索逻辑
        return [{"chunk_id": "...", "text": "...", "score": 0.9, "source": "my_retriever"}]
```

## 注意事项

- 切分器的 `chunk()` 方法是同步的
- 检索器的 `retrieve()` 方法是异步的
- 返回结果应包含 `source` 字段标记来源，便于混合检索区分
