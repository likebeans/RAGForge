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
| `hyde` | `HyDERetriever` | HyDE 检索器（LLM 生成假设文档嵌入） |
| `multi_query` | `MultiQueryRetriever` | 多查询扩展（LLM 生成查询变体，RRF 融合） |

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

### DenseRetriever
- `embedding_config`: 可选，动态 embedding 配置（来自知识库配置）

### BM25Retriever
- 无构造参数，使用全局配置

### HybridRetriever
- `dense_weight`: 稠密检索权重，默认 0.7
- `sparse_weight`: 稀疏检索权重，默认 0.3
- `embedding_config`: 可选，动态 embedding 配置

### LlamaDenseRetriever
- `top_k`: 默认返回数量，默认 5
- `store_type`: 向量存储类型（"qdrant" | "milvus" | "es"），默认 "qdrant"
- `store_params`: 存储参数（如 Milvus 的 index_params、ES 的 body）
- `embedding_config`: 可选，动态 embedding 配置

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
- `dense_weight`: 稠密检索权重，默认 0.7
- `bm25_weight`: BM25 检索权重，默认 0.3
- `rrf_k`: RRF 参数，默认 60
- `rerank`: 是否启用 Rerank，默认 False
- `rerank_model`: Rerank 模型名称
- `embedding_config`: 可选，动态 embedding 配置

### HyDERetriever
- `base_retriever`: 底层检索器类型，默认 "dense"
- `num_queries`: 生成假设文档数量，默认 3
- `include_original`: 是否保留原始查询，默认 True
- `max_tokens`: LLM 生成最大 token 数，默认 2000（qwen3 thinking 模式需要）
- `base_retriever_params`: 传递给底层检索器的参数（包括 `embedding_config`）

### MultiQueryRetriever
- `base_retriever`: 底层检索器名称，默认 "dense"
- `num_queries`: 生成的查询变体数量，默认 3
- `include_original`: 是否保留原始查询，默认 True
- `rrf_k`: RRF 融合常数，默认 60
- `base_retriever_params`: 传递给底层检索器的参数（包括 `embedding_config`）

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

# HyDE 检索（LLM 生成假设文档）
retriever = operator_registry.get("retriever", "hyde")(
    base_retriever="dense",
    num_queries=3,
)
results = await retriever.retrieve(
    query="这个药物有什么禁忌？",
    tenant_id="tenant_001",
    kb_ids=["kb_medical"],
    top_k=5
)
# results[0]["hyde_queries"] 包含 LLM 生成的假设文档

# MultiQuery 检索（LLM 生成查询变体）
retriever = operator_registry.get("retriever", "multi_query")(
    base_retriever="dense",
    num_queries=3,
)
results = await retriever.retrieve(
    query="这个药物的用法用量是什么？",
    tenant_id="tenant_001",
    kb_ids=["kb_medical"],
    top_k=5
)
# results[0]["generated_queries"] 包含 LLM 生成的查询变体
# results[0]["retrieval_details"] 包含每个查询的完整检索结果
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
    "source": str,             # 来源标记（"dense" | "bm25" | "hyde" | "multi_query"）
}
```

### HyDE 检索器扩展字段

```python
{
    "hyde_queries": list[str],      # LLM 生成的假设文档列表
    "hyde_queries_count": int,      # 假设文档数量
}
```

### MultiQuery 检索器扩展字段

```python
{
    "generated_queries": list[str],  # LLM 生成的查询变体列表
    "queries_count": int,            # 查询变体数量
    "retrieval_details": [           # 每个查询的完整检索结果
        {
            "query": str,            # 查询文本
            "hits_count": int,       # 检索到的 chunk 数量
            "hits": [                # 完整的检索结果列表
                {"chunk_id": ..., "text": ..., "score": ...}
            ]
        }
    ]
}
```

## BM25 分数归一化

BM25 原始分数是基于词频和文档长度计算的相关性分数，**没有固定上限**（可能是 3.0、5.0 甚至更高），而向量检索分数通常在 0-1 范围内。

为了确保混合检索时权重能正确生效，`bm25` 和 `llama_bm25` 检索器会对分数进行 **Min-Max 归一化**：

```python
normalized_score = (score - min_score) / (max_score - min_score)
```

| 归一化结果 | 说明 |
|-----------|------|
| 最高分 → 1.0 | 当前批次中最相关的文档 |
| 最低分 → 0.0 | 当前批次中最不相关的文档 |
| 所有分数相同 | 若 > 0 归一化为 1.0，否则为 0.0 |

**为什么需要归一化？**

假设 BM25 原始分数为 3.18，向量分数为 0.57，权重配置为 BM25=30%、向量=70%：

| 状态 | 计算 | 结果 |
|------|------|------|
| **归一化前** | `3.18 × 0.3 + 0.57 × 0.7` | 1.35（BM25 贡献过大） |
| **归一化后** | `1.0 × 0.3 + 0.57 × 0.7` | 0.70（权重正确生效） |

## 混合检索权重调优

| 权重配置 | 适用场景 |
|----------|----------|
| dense=0.7, bm25=0.3 | 通用问答（默认） |
| dense=0.5, bm25=0.5 | 平衡场景 |
| dense=0.3, bm25=0.7 | 术语/实体检索 |
| dense=0.9, bm25=0.1 | 纯语义匹配 |

## 动态 Embedding 配置

检索器支持从知识库配置中读取 embedding 模型，确保检索时使用与入库时相同的模型：

```python
# 检索服务会自动从知识库配置提取 embedding_config
embedding_config = {
    "provider": "ollama",
    "model": "bge-m3",
    "base_url": "http://localhost:11434",
}

# 支持动态配置的检索器
retriever = operator_registry.get("retriever", "dense")(
    embedding_config=embedding_config
)

# HyDE/MultiQuery 通过 base_retriever_params 传递
retriever = operator_registry.get("retriever", "hyde")(
    base_retriever="dense",
    base_retriever_params={"embedding_config": embedding_config}
)
```

**支持动态配置的检索器**：
- `dense` / `hybrid` / `fusion` / `llama_dense`：直接接受 `embedding_config`
- `hyde` / `multi_query`：通过 `base_retriever_params` 传递给底层检索器

## 添加新检索器

1. 创建新文件 `my_retriever.py`
2. 实现 `BaseRetrieverOperator` 协议（异步 `retrieve` 方法）
3. 使用装饰器注册：`@register_operator("retriever", "my_retriever")`
4. 在 `__init__.py` 中导入
5. 返回结果包含 `source` 字段标记来源
6. 如需支持动态 embedding，添加 `embedding_config` 参数
