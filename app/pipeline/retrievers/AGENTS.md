# Retrievers 检索器模块

检索器实现，提供多种检索策略从向量库和 BM25 索引中召回相关片段。

## 模块职责

- 提供稠密向量检索（语义匹配）
- 提供稀疏 BM25 检索（关键词匹配）
- 提供混合检索（加权融合）
- 支持多种向量存储后端（Qdrant、Milvus、Elasticsearch）

## 可用检索器

### 原生实现
| 名称 | 类 | 说明 |
|------|-----|------|
| `dense` | `DenseRetriever` | 基于 Qdrant 的稠密向量检索 |
| `bm25` | `BM25Retriever` | 基于内存 BM25 的稀疏检索 |
| `hybrid` | `HybridRetriever` | Dense + BM25 加权融合 |
| `fusion` | `FusionRetriever` | 融合检索（RRF/加权 + 可选 Rerank） |
| `hyde` | `HyDERetriever` | HyDE 检索器（假设文档嵌入） |

### LlamaIndex 实现
| 名称 | 类 | 说明 |
|------|-----|------|
| `llama_dense` | `LlamaDenseRetriever` | LlamaIndex 稠密检索，支持多后端 |
| `llama_bm25` | `LlamaBM25Retriever` | LlamaIndex BM25 检索，带缓存 |
| `llama_hybrid` | `LlamaHybridRetriever` | LlamaIndex 混合检索 |

## 检索器选型建议

| 场景 | 推荐检索器 | 原因 |
|------|-----------|------|
| 通用问答 | `hybrid` | 兼顾语义和关键词 |
| 语义相似 | `dense` | 捕获深层语义 |
| 精确匹配 | `bm25` | 术语、实体检索 |
| 多后端切换 | `llama_dense` | 支持 Qdrant/Milvus/ES |
| 大规模数据 | `llama_bm25` | 带 TTL 缓存，减少 DB 查询 |

## 参数说明

### DenseRetriever / BM25Retriever
- 无构造参数，使用全局配置

### HybridRetriever
- `dense_weight`: 稠密检索权重，默认 0.7
- `sparse_weight`: 稀疏检索权重，默认 0.3

### LlamaDenseRetriever
- `top_k`: 默认返回数量，默认 5
- `store_type`: 向量存储类型（"qdrant" | "milvus" | "es"），默认 "qdrant"
- `store_params`: 存储参数（如 Milvus 的 index_params、ES 的 body）

### LlamaBM25Retriever
- `top_k`: 默认返回数量，默认 5
- `max_chunks`: 最大加载片段数，默认 5000
- `cache_ttl`: 缓存过期时间（秒），默认 60

### LlamaHybridRetriever
- `dense_weight`: 稠密检索权重，默认 0.7
- `bm25_weight`: BM25 检索权重，默认 0.3
- `top_k`: 默认返回数量，默认 5

### FusionRetriever
- `mode`: 融合模式（"rrf" | "weighted"），默认 "rrf"
- `weights`: 各检索器权重，默认 `{"dense": 0.5, "bm25": 0.5}`
- `rrf_k`: RRF 参数，默认 60
- `use_rerank`: 是否启用 Rerank，默认 False
- `rerank_model`: Rerank 模型名称

### HyDERetriever
- `hyde_config`: HyDE 配置（模型、最大 token 等）
- `base_retriever`: 底层检索器类型，默认 "hybrid"
- `num_hypotheses`: 生成假设文档数量，默认 1

## 使用示例

```python
from app.pipeline import operator_registry

# 混合检索（推荐）
retriever = operator_registry.get("retriever", "hybrid")(
    dense_weight=0.6,
    sparse_weight=0.4
)
results = await retriever.retrieve(
    query="什么是知识图谱？",
    tenant_id="tenant_001",
    kb_ids=["kb_tech"],
    top_k=10
)

# LlamaIndex + Milvus
retriever = operator_registry.get("retriever", "llama_dense")(
    store_type="milvus",
    store_params={
        "index_params": {"index_type": "IVF_PQ", "metric_type": "COSINE", "params": {"nlist": 128, "m": 16}}
    }
)
```

## 输出格式

所有检索器返回 `list[dict]`：

```python
{
    "chunk_id": str,           # 片段 ID
    "text": str,               # 片段文本
    "score": float,            # 相关性分数
    "metadata": dict,          # 元数据
    "knowledge_base_id": str,  # 所属知识库 ID
    "document_id": str | None, # 所属文档 ID
    "source": str,             # 来源标记（"dense" | "bm25"）
}
```

## 混合检索权重调优

| 权重配置 | 适用场景 |
|----------|----------|
| dense=0.7, bm25=0.3 | 通用问答（默认） |
| dense=0.5, bm25=0.5 | 平衡场景 |
| dense=0.3, bm25=0.7 | 术语/实体检索 |
| dense=0.9, bm25=0.1 | 纯语义匹配 |

## 添加新检索器

1. 创建新文件 `my_retriever.py`
2. 实现 `BaseRetrieverOperator` 协议（异步 `retrieve` 方法）
3. 使用装饰器注册：`@register_operator("retriever", "my_retriever")`
4. 在 `__init__.py` 中导入
5. 返回结果包含 `source` 字段标记来源
