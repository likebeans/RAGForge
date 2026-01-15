# 管道架构文档

本文档详细描述 Self-RAG Pipeline 的可插拔算法框架设计、组件实现和优化策略。

## 架构概览

Self-RAG Pipeline 采用可插拔的算法框架，支持动态注册和发现算法组件，实现了灵活的检索增强生成系统。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline 算法框架                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Chunkers  │  │ Retrievers  │  │ Enrichers   │  │Postprocessors│ │
│  │   切分器     │  │   检索器     │  │   增强器     │  │   后处理器   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │Query Transforms│ │  Indexers  │  │  Registry   │                  │
│  │  查询变换器   │  │   索引器    │  │  注册表     │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 切分器 (Chunkers)

负责将文档切分为适合检索的文本块。

#### 可用切分器

| 名称 | 实现 | 适用场景 |
|------|------|---------|
| `simple` | 按 `\n\n` 分段 | 简单场景 |
| `sliding_window` | 固定窗口滑动 | 通用文档 |
| `parent_child` | 父子分块 | 长文章、保留上下文 |
| `recursive` | 递归字符分割（`\n\n` → `\n` → ` ` → `""`） | 通用文档（推荐） |
| `markdown` | 按 Markdown 标题层级分块 | 文档/Wiki/README |
| `code` | 按代码语法结构分块（class/function/def） | 代码文档 |
| `llama_sentence` | LlamaIndex 句子级 | 精确问答 |
| `llama_token` | LlamaIndex Token 级 | Token 敏感场景 |

#### 分块元数据标准

所有切分器必须写入以下 metadata：

```python
{
    "chunk_order": int,       # 块序号
    "document_id": str,       # 所属文档 ID
    "tenant_id": str,         # 租户 ID
    "kb_id": str,             # 知识库 ID
    "title": str,             # 文档标题
    "page_number": int,       # 页码（可选）
    "parent_id": str,         # 父块 ID（parent_child 模式）
}
```

#### 使用示例

```python
from app.pipeline import operator_registry

# 递归切分（推荐用于通用文档）
chunker = operator_registry.get('chunker', 'recursive')(
    chunk_size=1024, 
    chunk_overlap=256
)
pieces = chunker.chunk("长文本...")

# Markdown 切分（推荐用于文档/Wiki）
md_chunker = operator_registry.get('chunker', 'markdown')(chunk_size=1024)
pieces = md_chunker.chunk("# 标题\n内容...")
```

### 2. 检索器 (Retrievers)

实现不同的检索策略，支持语义检索、关键词检索和混合检索。

#### 检索器类型

| 名称 | 说明 | 适用场景 |
|------|------|---------|
| `dense` | 稠密向量检索 | 语义相似性查询 |
| `hybrid` | 混合检索（Dense + BM25，带 source 标记） | 平衡精确性和召回率 |
| `fusion` | 融合检索（RRF/加权 + 可选 Rerank） | 高质量检索 |
| `hyde` | HyDE 检索器（LLM 生成假设文档嵌入） | 零样本/领域冷启动 |
| `multi_query` | 多查询扩展检索（LLM 生成查询变体，RRF 融合） | 提高召回覆盖率 |
| `self_query` | 自查询检索（LLM 解析元数据过滤条件） | 结构化查询 |
| `parent_document` | 父文档检索（小块检索返回父块上下文） | 需要完整上下文 |
| `ensemble` | 集成检索（任意组合多检索器） | 复杂检索需求 |
| `raptor` | RAPTOR 多层次索引检索（递归聚类+摘要树） | 长文档层次检索 |

#### 检索器兼容性

部分检索器对知识库配置有特殊要求：

| 检索器 | 要求 | 说明 |
|--------|------|------|
| `raptor` | RAPTOR 索引 | 需要在入库时启用 RAPTOR 索引增强 |
| `parent_document` | `parent_child` 切分器 | 需要使用父子分块切分器入库 |

#### 推荐配置

```python
# 分块配置
chunk_size = 1024
chunk_overlap = 256

# 检索配置
similarity_top_k = 20      # 向量召回数
bm25_top_k = 20            # BM25 召回数
rerank_top_k = 30          # 融合后送入 rerank 的数量
final_top_k = 10           # 最终返回数

# RRF 融合权重
dense_weight = 0.7
sparse_weight = 0.3
```

### 3. 查询变换器 (Query Transforms)

在检索前对查询进行预处理和增强。

#### 可用变换器

| 名称 | 说明 | 用途 |
|------|------|------|
| `HyDEQueryTransform` | 假设文档嵌入查询变换 | 生成假设答案用于检索 |
| `QueryRouter` | 查询路由，自动选择检索策略 | 智能路由到最佳检索器 |
| `RAGFusionTransform` | 多查询扩展 | 生成查询变体提高召回 |

#### 使用示例

```python
from app.pipeline.query_transforms import HyDEQueryTransform, QueryRouter

# HyDE 查询变换
transform = HyDEQueryTransform(num_queries=4)
hypothetical_docs = await transform.agenerate(query="什么是RAG？")

# 查询路由
router = QueryRouter(use_llm=False)  # 规则路由（快速）
result = router.route("什么是 RAG？")
print(result.retriever)  # "dense"
```

### 4. 文档增强器 (Enrichers)

在入库前为文档或 Chunk 添加额外的上下文信息。

#### DocumentSummarizer - 文档摘要生成

对整个文档生成全局摘要，提供文档的整体上下文。

**配置选项**：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `summary_length` | 摘要长度（short/medium/long） | medium |
| `prepend_summary` | 是否将摘要前置到每个 chunk | true |

**使用场景**：
- **开启**：长文档、技术报告、多主题文档（需要全局上下文）
- **关闭**：短文档、Chunk 本身已足够完整、节省嵌入 Token

#### ChunkEnricher - Chunk 上下文增强

为每个 Chunk 添加上下文信息（如前后文摘要、章节标题等），默认关闭。

**配置选项**：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `context_window` | 上下文窗口大小 | 1 |
| `include_headers` | 是否包含章节标题 | true |

### 5. 后处理器 (Postprocessors)

对检索结果进行后处理和优化。

#### ContextWindowExpander

扩展检索到的 Chunk 的上下文窗口，包含前后相邻的文本块。

**配置选项**：
```python
ContextWindowConfig(
    enabled=True,
    before=1,        # 前文块数
    after=1,         # 后文块数
    max_tokens=2048  # 最大 token 数
)
```

### 6. 索引器 (Indexers)

#### RAPTOR 索引器

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 是一种多层次索引方法。

**核心原理**：
```
Layer 3 (Root):      [Global Summary]
                          │
Layer 2:          [Summary A]  [Summary B]
                    /    \        /    \
Layer 1:        [S1]    [S2]   [S3]   [S4]
                 / \     |      |    /   \
Layer 0:      [C1][C2] [C3]   [C4] [C5] [C6]  (原始Chunks)
```

**构建流程**：
1. 将原始 Chunks 向量化
2. 使用聚类算法（GMM/K-Means）对相似 Chunks 分组
3. 对每个聚类生成摘要（LLM）
4. 将摘要作为新节点，递归处理直到达到最大层数

**检索模式**：
- `collapsed`: 所有层级节点扁平化，统一 top-k 检索（速度快）
- `tree_traversal`: 从顶层开始，逐层向下筛选（更精确）

## 查询管线示例

```python
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.vector_stores.qdrant import QdrantVectorStore

# 1. 分块
splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=256)
nodes = splitter.get_nodes_from_documents(documents)

# 2. 构建索引
vector_store = QdrantVectorStore(client=qdrant_client, collection_name="kb_xxx")
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex(nodes, storage_context=storage_context)

# 3. 构建检索器
vec_retriever = index.as_retriever(similarity_top_k=20)
bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=20)

# 4. 混合检索 + RRF 融合
fused_retriever = QueryFusionRetriever(
    retrievers=[vec_retriever, bm25_retriever],
    num_queries=1,           # 不使用 HyDE 时设为 1
    mode="reciprocal_rerank",
)

# 5. 重排
reranker = SentenceTransformerRerank(
    model="BAAI/bge-reranker-base",
    top_n=10,
)

# 6. 执行检索
nodes = fused_retriever.retrieve("用户问题")
nodes = reranker.postprocess_nodes(nodes)
```

## 上下文增强策略

### 启用条件与触发机制

| 方法 | 阶段 | 原理 | 启用条件/触发 | 适用场景 |
|------|------|------|---------------|----------|
| Context Window | 检索后 | 扩展命中 chunk 的前后 N 个 | 默认开启，N 可配置 | 长文、需要上下文连贯 |
| Document Summary | 索引时 | 生成摘要用于路由/过滤/展示 | 文档长度 > 阈值或 KB 级启用；失败回退 | 多知识库、长文 |
| HyDE | 查询时 | 生成假设答案，再用其嵌入检索 | 召回不足（如 top_k 低于阈值）或冷启动时触发 | 零样本/领域冷启动 |
| Chunk Enrichment | 索引时 | LLM 重写 chunk，融合前后文，再嵌入 | 明确白名单数据集，成本可接受时；默认关 | 高精场景 |

### 配置示例

```python
# 检索阶段
context_window = {"enabled": True, "before": 1, "after": 1, "max_tokens": 2048}
hyde = {
    "enabled": True,
    "trigger_top_k_threshold": 5,  # 命中不足时触发
    "num_queries": 4,
    "include_original": True,
    "max_tokens": 256,
}

# 索引阶段
document_summary = {
    "enabled": True,
    "min_tokens": 2000,      # 文档超过再生成
    "model": "gpt-4o-mini",
    "max_tokens": 256,
    "cache": True,
}
chunk_enrichment = {
    "enabled": False,        # 默认关闭
    "n_neighbors": 2,        # 取前后邻居拼接提示
    "model": "gpt-4o-mini",
    "max_tokens": 256,
    "max_chunk_size": 1024,  # 生成后截断
    "cache": True,
    "rate_limit_qps": 2,
}
```

## 检索策略组合

### 按复杂度递进的检索策略

| 阶段 | 策略 | 配置 |
|------|------|------|
| **基础** | 语义检索 | `VectorIndexRetriever(similarity_top_k=20)` |
| **混合** | 语义 + BM25 + RRF 融合 | `QueryFusionRetriever(mode="reciprocal_rerank")` |
| **增强** | HyDE 多查询扩展 | `HyDEQueryTransform(num_queries=4)` |
| **精排** | Cross-encoder 重排 | `SentenceTransformerRerank(top_n=10)` |

### 融合检索算法

#### RRF (Reciprocal Rank Fusion)

```python
# RRF 融合算法实现
def rrf_fusion(results_list: list[list], k: int = 60) -> list:
    """
    RRF 融合算法
    公式：score = sum(1 / (k + rank_i))
    """
    doc_scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc.id
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"doc": doc, "score": 0}
            doc_scores[doc_id]["score"] += 1 / (k + rank + 1)
    
    # 按分数降序排序
    return sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
```

## 模型配置动态化

### 配置优先级

**请求级 > 知识库级 > 租户级 > 系统级 > 环境变量默认**

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐
│  API 请求     │  │ KnowledgeBase │  │   Tenant     │  │ SystemConfig │
│  llm_model   │  │ embedding_*  │  │ default_*    │  │ (数据库)     │
│  rerank_*    │  │ (创建时固定)  │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘
       ↓                 ↓                 ↓                 ↓
                    配置解析器 (合并优先级)
                           ↓
                    infra 层调用模型
```

### 不同模型的配置策略

| 模型类型 | 配置层级 | 说明 |
|---------|---------|------|
| **Embedding** | 知识库级（固定） | 创建 KB 时确定，不可变（向量维度绑定） |
| **LLM** | 请求/租户/系统 | 动态切换，用于 HyDE/RAG 等 |
| **Rerank** | 请求/租户/系统 | 动态切换，检索后处理 |

## 性能优化

### 批量处理

- 向量化：支持批量 embedding 调用
- 数据库写入：使用批量 upsert 操作
- 检索：并行执行多路检索器

### 缓存策略

- LLM 生成结果缓存（HyDE、摘要等）
- Embedding 结果缓存
- 检索结果缓存（基于查询哈希）

### 异步处理

- 所有 I/O 操作使用 async/await
- 数据库连接池管理
- 向量库异步客户端

## 扩展性设计

### 插件注册机制

```python
from app.pipeline import operator_registry

# 注册新的切分器
@operator_registry.register("chunker", "custom")
class CustomChunker(BaseChunker):
    def chunk(self, text: str) -> list[ChunkPiece]:
        # 自定义切分逻辑
        pass

# 注册新的检索器
@operator_registry.register("retriever", "custom")
class CustomRetriever(BaseRetriever):
    async def retrieve(self, query: str, **kwargs) -> list[ChunkResult]:
        # 自定义检索逻辑
        pass
```

### 配置驱动

所有算法组件都支持通过配置文件或 API 参数进行定制，无需修改代码即可调整行为。

## 监控与调试

### 检索响应包含模型信息

```json
{
  "results": [...],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "rerank_provider": null,
    "rerank_model": null,
    "retriever": "hybrid"
  }
}
```

### 可视化字段

- `hyde_queries`: HyDE 检索器返回 LLM 生成的假设文档
- `semantic_query`: Self-Query 检索器返回 LLM 提取的语义查询
- `parsed_filters`: Self-Query 检索器返回 LLM 解析的元数据过滤条件
- `generated_queries`: Multi-Query 检索器返回 LLM 生成的查询变体

这些字段在 Rerank 后会自动保留，确保前端可视化正常显示。