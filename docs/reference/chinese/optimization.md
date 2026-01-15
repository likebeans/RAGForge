# 知识库检索优化方案

> 借鉴 R2R 项目的分块、检索架构，基于 LlamaIndex 实现可落地的知识库检索系统。

---

## 一、架构对比：R2R vs 本项目

| 模块 | R2R 做法 | 本项目做法（LlamaIndex） |
|------|---------|------------------------|
| **分块** | 自建 `RecursiveCharacterTextSplitter`（移植自 LangChain） | `SentenceSplitter` / `TokenTextSplitter` |
| **语言感知** | 支持 Python/JS/TS/Markdown 等语法结构分块 | 待实现 |
| **文件解析** | 内置 30+ 格式解析器 | 纯文本输入，待扩展 |
| **向量存储** | PostgreSQL + pgvector | Qdrant（默认）/ Milvus / ES |
| **检索策略** | 自建 Provider | LlamaIndex Retriever |

---

## 二、分块策略优化

### 2.1 现有切分器

| 名称 | 实现 | 适用场景 |
|------|------|---------|
| `simple` | 按 `\n\n` 分段 | 简单场景 |
| `sliding_window` | 固定窗口滑动 | 通用文档 |
| `parent_child` | 父子分块 | 长文章、保留上下文 |
| `recursive` | 递归字符分割（`\n\n` → `\n` → ` ` → `""`） | 通用文档（推荐） |
| `markdown` | 按 Markdown 标题层级分块 | 文档/Wiki/README |
| `llama_sentence` | LlamaIndex 句子级 | 精确问答 |
| `llama_token` | LlamaIndex Token 级 | Token 敏感场景 |

### 2.2 待新增切分器（借鉴 R2R）

| 名称 | 说明 | 优先级 |
|------|------|--------|
| `code` | 按代码语法结构分块（class/function/def） | P2 |

### 2.3 分块元数据标准

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

---

## 三、检索策略

### 3.1 检索器组合（按复杂度递进）

| 阶段 | 策略 | 配置 |
|------|------|------|
| **基础** | 语义检索 | `VectorIndexRetriever(similarity_top_k=20)` |
| **混合** | 语义 + BM25 + RRF 融合 | `QueryFusionRetriever(mode="reciprocal_rerank")` |
| **增强** | HyDE 多查询扩展 | `HyDEQueryTransform(num_queries=4)` |
| **精排** | Cross-encoder 重排 | `SentenceTransformerRerank(top_n=10)` |

### 3.2 推荐配置

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

---

## 四、查询管线示例

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

---

## 五、质量增强（可选）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| **文档摘要** | 对前 N 个 chunk 生成摘要，用于路由/过滤 | P2 |
| **Chunk Enrichment** | LLM 对 chunk 做上下文扩写后重嵌入 | P3 |
| **多查询扩展** | HyDE 或 MultiStep 生成多个查询变体 | P2 |

---

## 六、开发计划

### Phase 1：分块优化 ✅ 已完成（2024-12-02）

**完成内容：**

1. **新增 `recursive` 递归字符切分器**
   - 文件：`app/pipeline/chunkers/recursive.py`
   - 借鉴 R2R 的 `RecursiveCharacterTextSplitter` 实现
   - 按优先级尝试分隔符：`\n\n` → `\n` → ` ` → `""`
   - 支持 `chunk_size`、`chunk_overlap`、`keep_separator` 参数

2. **新增 `markdown` Markdown 感知切分器**
   - 文件：`app/pipeline/chunkers/markdown.py`
   - 按 Markdown 标题（# / ## / ### / ####）分块
   - 自动提取标题层级信息到 metadata（如 `{"h1": "标题", "h2": "子标题"}`）
   - 超长片段自动二次分割

3. **修复依赖问题**
   - 升级 `qdrant-client` 1.9.2 → 1.15.1
   - 修复 `BM25Retriever` 导入路径：`llama_index.retrievers.bm25`
   - 修复循环导入：延迟导入 `collect_chunks_for_kbs`

**使用示例：**
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
# pieces[0].metadata = {"h1": "标题"}
```

- [x] 新增 `recursive` 递归字符切分器
- [x] 新增 `markdown` Markdown 感知切分器
- [ ] 统一 metadata 字段规范（待后续完善）

---

### Phase 2：检索增强 ✅ 已完成（2024-12-02）

**完成内容：**

1. **新增 `fusion` 融合检索器**
   - 文件：`app/pipeline/retrievers/fusion.py`
   - 支持两种融合模式：
     - `rrf`: Reciprocal Rank Fusion（推荐）
     - `weighted`: 加权融合
   - 可选 Rerank 精排（需安装 `sentence-transformers`）

2. **RRF 融合算法实现**
   - 公式：`score = sum(1 / (k + rank_i))`
   - 默认 k=60（论文推荐值）
   - 自动合并多路召回结果

3. **Rerank 集成**
   - 使用 `sentence-transformers` 的 `CrossEncoder`
   - 默认模型：`BAAI/bge-reranker-base`
   - 可配置 `rerank_top_n` 控制重排数量

**使用示例：**
```python
from app.pipeline import operator_registry

# RRF 融合（推荐）
retriever = operator_registry.get('retriever', 'fusion')(
    mode='rrf',
    rrf_k=60,
    top_k=20,
)

# RRF + Rerank（需安装 sentence-transformers）
retriever = operator_registry.get('retriever', 'fusion')(
    mode='rrf',
    rerank=True,
    rerank_model='BAAI/bge-reranker-base',
    rerank_top_n=10,
)

# 加权融合
retriever = operator_registry.get('retriever', 'fusion')(
    mode='weighted',
    dense_weight=0.7,
    bm25_weight=0.3,
)
```

**启用 Rerank 需安装：**
```bash
uv add sentence-transformers
```

- [x] 集成融合检索（RRF + 加权）
- [x] 集成 `SentenceTransformerRerank` 重排
- [x] 实现 RRF 融合算法

### Phase 3：上下文增强

> 目标：在保证成本/延迟可控的前提下提升召回质量和上下文完整性，优先小步上线、可回退。

#### 3.0 上线策略（先易后难，默认可回退）
- **P0 默认开**：Context Window（命中 chunk 前后 N 个）——无额外 LLM 成本。
- **P1 可选**：Document Summary（索引时生成摘要，供路由/过滤），HyDE（召回不足时触发）。
- **P2 可选且默认关**：Chunk Enrichment（LLM 扩写 chunk，重嵌入）。需限流与缓存。
- 所有能力需有开关与回退：失败时回退原始 chunk/查询，不阻塞检索链路。

#### 3.1 方法概览与启用条件

| 方法 | 阶段 | 原理 | 启用条件/触发 | 适用场景 |
|------|------|------|---------------|----------|
| Context Window | 检索后 | 扩展命中 chunk 的前后 N 个 | 默认开启，N 可配置 | 长文、需要上下文连贯 |
| Document Summary | 索引时 | 生成摘要用于路由/过滤/展示 | 文档长度 > 阈值或 KB 级启用；失败回退 | 多知识库、长文 |
| HyDE | 查询时 | 生成假设答案，再用其嵌入检索 | 召回不足（如 top_k 低于阈值）或冷启动时触发 | 零样本/领域冷启动 |
| Chunk Enrichment | 索引时 | LLM 重写 chunk，融合前后文，再嵌入 | 明确白名单数据集，成本可接受时；默认关 | 高精场景 |

#### 3.2 配置与开关（建议）
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

#### 3.3 Context Window（先上线）
- 逻辑：检索后按 `document_id` + `chunk_order` 扩展前后 N 个；仅在同一文档内扩展。
- 限制：全局返回长度不超过 `max_tokens`；若溢出，先保留命中 chunk，再按距离截断。
- 回退：找不到相邻块时仅返回命中块。

#### 3.4 Document Summary（按需开启）
- 触发：文档 token 数 > `min_tokens` 或知识库标记需要摘要。
- 生成：便宜模型短摘要，缓存键包含 `doc_id + version`。
- 用途：查询路由/过滤提示；不直接替代正文内容。
- 回退：LLM 失败时跳过摘要，不影响索引。

#### 3.5 HyDE（条件触发）
- 触发：召回 top_k < `trigger_top_k_threshold` 或明确冷启动问题。
- 策略：`include_original=True` 保留原查询；`num_queries` 控制成本；`max_tokens` 限制假设答案长度。
- 监控：记录触发率、额外延迟、命中率提升。

#### 3.6 Chunk Enrichment（慎用，默认关）
- 目的：补全上下文/消歧并重嵌入，适用于高精领域。
- 索引策略：
  - 方案 A：同一向量字段存“原文+增强描述”文本，metadata 保存 `original_text`。
  - 方案 B（推荐安全）：双索引/双字段（原文 vs 增强），检索后融合或仅 rerank 阶段使用增强文本，避免覆盖原文。
- 成本控制：缓存生成结果；设置 QPS 与批量；超时/失败回退原文。
- 追溯：metadata 记录 `original_text` 和 `enrichment_status`。

#### 3.7 评估与监控
- 评估集：选择真实问答集，记录 baseline（Phase 2）与各增强策略的命中率/MAP/MRR、延迟、成本。
- 指标：LLM 调用数、缓存命中率、平均延迟、HyDE 触发率、Context Window 展开后长度分布。
- 验收：每个子功能需证明对基线有正增益或延迟可接受，否则默认关闭。

#### 3.8 开发任务（更新）
| 任务 | 优先级 | 复杂度 | 状态 |
|------|--------|--------|------|
| Context Window | P0 | 低 | ✅ 已完成 |
| HyDE | P1 | 中 | ✅ 已完成 |
| Document Summary | P1 | 中 | ✅ 已完成 |
| Chunk Enrichment | P2 | 高 | ✅ 已完成 |

**Context Window 完成内容（2024-12-02）**：
- 文件：`app/pipeline/postprocessors/context_window.py`
- 修改：`app/services/ingestion.py` 自动添加 `chunk_index` 到 metadata
- 修改：`app/services/query.py` 检索后自动扩展上下文
- 配置：`ContextWindowConfig(enabled=True, before=1, after=1, max_tokens=2048)`

```python
# 使用示例
from app.pipeline.postprocessors.context_window import ContextWindowConfig

# 检索时自动启用（默认）
results = await retrieve_chunks(
    tenant_id=tenant_id,
    kbs=kbs,
    query=query,
    top_k=10,
    session=db,
)
# 返回结果包含 context_text, context_before, context_after

# 自定义配置
config = ContextWindowConfig(before=2, after=2, max_tokens=4096)
results = await retrieve_chunks(..., context_window=config)

# 禁用
config = ContextWindowConfig(enabled=False)
results = await retrieve_chunks(..., context_window=config)
```

- [x] Context Window：检索后扩展上下文，控制长度
- [x] HyDE：假设文档嵌入检索
- [x] Document Summary：阈值触发 + 回退
- [x] Chunk Enrichment：双字段存储，默认关闭

**HyDE 完成内容（2024-12-02）**：
- 文件：`app/pipeline/query_transforms/hyde.py` - HyDE 查询变换器
- 文件：`app/pipeline/retrievers/hyde.py` - HyDE 检索器（封装任意底层检索器）
- 配置：`app/config.py` 添加 LLM 和 HyDE 配置

环境变量：
```bash
OPENAI_API_KEY=sk-xxx           # 必需
OPENAI_API_BASE=https://...     # 可选，自定义 API 端点
OPENAI_MODEL=gpt-4o-mini        # 默认模型
HYDE_ENABLED=true               # 是否启用 HyDE
HYDE_NUM_QUERIES=4              # 假设答案数量
HYDE_INCLUDE_ORIGINAL=true      # 是否保留原始查询
HYDE_MAX_TOKENS=256             # 假设答案最大长度
```

使用示例：
```python
from app.pipeline import operator_registry

# 使用 HyDE 检索器（封装 dense 检索器）
retriever = operator_registry.get("retriever", "hyde")(
    base_retriever="dense",  # 底层检索器
    hyde_config=HyDEConfig(num_queries=4),
)
results = await retriever.retrieve(
    query="什么是RAG？",
    tenant_id=tenant_id,
    kb_ids=kb_ids,
    top_k=10,
)

# 或直接使用查询变换器
from app.pipeline.query_transforms import HyDEQueryTransform
transform = HyDEQueryTransform(num_queries=4)
hypothetical_docs = await transform.agenerate(query="什么是RAG？")
# 返回 ["RAG是一种结合检索和生成的技术...", ...]
```

**Document Summary 完成内容（2024-12-02）**：
- 文件：`app/pipeline/enrichers/summarizer.py` - 文档摘要生成器
- 修改：`app/models/document.py` 添加 `summary` 和 `summary_status` 字段
- 修改：`app/services/ingestion.py` 文档摄取时自动生成摘要
- 配置：`app/config.py` 添加 Document Summary 配置

环境变量：
```bash
DOC_SUMMARY_ENABLED=true        # 是否启用文档摘要
DOC_SUMMARY_MIN_TOKENS=500      # 触发摘要的最小 token 数
DOC_SUMMARY_MAX_TOKENS=300      # 摘要最大 token 数
DOC_SUMMARY_MODEL=gpt-4o-mini   # 可选，默认使用 OPENAI_MODEL
```

使用示例：
```python
from app.pipeline.enrichers import DocumentSummarizer, generate_summary

# 方式1: 直接使用便捷函数
summary = await generate_summary(content="长文档内容...")

# 方式2: 使用类
summarizer = DocumentSummarizer(min_tokens=500, max_tokens=300)
summary = await summarizer.agenerate(content="长文档内容...")

# 方式3: 在文档摄取时自动生成
doc, chunks = await ingest_document(
    session=db,
    tenant_id=tenant_id,
    kb=kb,
    title="文档标题",
    content="文档内容...",
    metadata={},
    source="pdf",
    generate_doc_summary=True,  # 默认启用
)
# doc.summary 包含生成的摘要
# doc.summary_status 为 "completed" / "skipped" / "failed"
```

**注意**：Document 模型新增字段需要数据库迁移：
```bash
uv run alembic revision --autogenerate -m "add document summary fields"
uv run alembic upgrade head
```

**Chunk Enrichment 完成内容（2024-12-02）**：
- 文件：`app/pipeline/enrichers/chunk_enricher.py` - Chunk 增强器
- 修改：`app/models/chunk.py` 添加 `enriched_text` 和 `enrichment_status` 字段
- 修改：`app/services/ingestion.py` 支持可选的 chunk 增强
- 配置：`app/config.py` 添加 Chunk Enrichment 配置

环境变量：
```bash
CHUNK_ENRICHMENT_ENABLED=false      # 默认关闭（LLM 成本高）
CHUNK_ENRICHMENT_MAX_TOKENS=512     # 增强文本最大 token 数
CHUNK_ENRICHMENT_CONTEXT_CHUNKS=1   # 上下文 chunk 数量
```

使用示例：
```python
from app.pipeline.enrichers import ChunkEnricher, get_chunk_enricher

# 方式1: 在文档摄取时启用（需显式开启）
doc, chunks = await ingest_document(
    session=db,
    tenant_id=tenant_id,
    kb=kb,
    title="文档标题",
    content="文档内容...",
    metadata={},
    source="pdf",
    enrich_chunks=True,  # 显式启用
)

# 方式2: 直接使用增强器
enricher = ChunkEnricher(context_chunks=1)
enriched = await enricher.aenrich(
    chunk_text="原始文本...",
    doc_title="文档标题",
    preceding_chunks=["前文1"],
    succeeding_chunks=["后文1"],
)
```

**注意**：
- Chunk Enrichment **默认关闭**，因为会显著增加 LLM 调用成本
- 每个 chunk 需要一次 LLM 调用，大文档可能产生大量 API 费用
- 建议仅对高价值文档或小规模知识库启用

---

### Phase 4：智能检索 ✅ 已完成（2024-12-02）

> 目标：提供更智能的检索能力，包括代码感知分块、查询路由和多查询扩展。

#### 4.1 Code Chunker（代码感知分块）✅
- **文件**：`app/pipeline/chunkers/code.py`
- **目的**：按代码语法结构（class/function/method）分块，保持代码逻辑完整性
- **支持语言**：Python（AST 解析）、JavaScript/TypeScript、Java、Go、Rust（正则匹配）
- **metadata**：`{"language": "python", "block_type": "function", "name": "func_name", "line_start": 10, "line_end": 50}`

```python
from app.pipeline import operator_registry

chunker = operator_registry.get('chunker', 'code')(
    language='python',  # 或 'auto' 自动检测
    max_chunk_size=2000,
    include_imports=True,
)
pieces = chunker.chunk(code_text)
```

#### 4.2 Query Router（查询路由）✅
- **文件**：`app/pipeline/query_transforms/router.py`
- **目的**：根据查询类型自动选择最佳检索策略
- **路由策略**：
  - `semantic` → dense 检索
  - `keyword` → bm25 检索
  - `hybrid` → hybrid 检索
  - `code` → hybrid 检索

```python
from app.pipeline.query_transforms import QueryRouter, route_query

router = QueryRouter(use_llm=False)  # 规则路由（快速）
result = router.route("什么是 RAG？")
print(result.retriever)  # "dense"
print(result.query_type)  # QueryType.SEMANTIC

# 或使用便捷函数
result = route_query("def hello():")  # QueryType.CODE
```

#### 4.3 RAG Fusion（多查询扩展）✅
- **文件**：`app/pipeline/query_transforms/rag_fusion.py`
- **目的**：生成多个查询变体，提高召回覆盖率

```python
from app.pipeline.query_transforms import RAGFusionTransform, expand_query

# 方式1: 使用类
transform = RAGFusionTransform(num_queries=3)
queries = transform.generate("什么是 RAG？")
# 返回 ["什么是 RAG？", "RAG 技术是什么意思？", ...]

# 方式2: 便捷函数
queries = expand_query("什么是 RAG？", num_queries=3)
```

#### 4.4 开发任务
| 任务 | 优先级 | 复杂度 | 状态 |
|------|--------|--------|------|
| Code Chunker | P1 | 中 | ✅ 已完成 |
| Query Router | P1 | 中 | ✅ 已完成 |
| RAG Fusion | P2 | 低 | ✅ 已完成 |

---

### Phase 5：生产就绪（进行中）

> 目标：修复阻塞生产部署的关键问题，确保系统可靠性和可扩展性。

#### 5.1 发现的问题

| 问题 | 严重程度 | 文件 | 描述 |
|------|----------|------|------|
| **哈希向量不可复现** | 🔴 P0 致命 | `app/infra/embeddings.py` | 使用 Python `hash()` 做 embedding，每次重启随机种子不同，写入和查询向量不一致，检索不可用 |
| **阻塞事件循环** | 🔴 P0 严重 | `app/infra/vector_store.py` | Qdrant 同步客户端在异步路由中直接调用，阻塞事件循环 |
| **向量写入无事务** | 🟠 P1 高 | `app/services/ingestion.py` | 先写 DB 再写向量，向量失败会留下不可检索的 chunks，无回滚/补偿 |
| **BM25 内存不持久** | 🟠 P1 高 | `app/infra/bm25_store.py` | 内存实现，重启后丢失，需从 DB 重建 |
| **限流非集群安全** | 🟡 P2 中 | `app/auth/api_key.py` | 进程内内存限流，多实例部署无效 |
| **自动建表风险** | 🟡 P2 中 | `app/main.py` | 无条件调用 `init_models()`，生产环境应禁用 |

#### 5.2 修复计划

##### 5.2.1 Embedding 替换（P0）
- **问题**：`hash()` 不确定性 + 无语义
- **方案**：接入 OpenAI Embedding API（已有配置）
- **文件**：`app/infra/embeddings.py`

```python
# 替换后
from openai import AsyncOpenAI

async def get_embedding(text: str) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
```

##### 5.2.2 异步化 Qdrant（P0）
- **问题**：同步调用阻塞事件循环
- **方案**：使用 `qdrant_client.AsyncQdrantClient`
- **文件**：`app/infra/vector_store.py`

```python
# 替换后
from qdrant_client import AsyncQdrantClient

class AsyncQdrantVectorStore:
    async def upsert_chunk(self, ...) -> None:
        await self.client.upsert(...)
    
    async def search(self, ...) -> list[...]:
        return await self.client.search(...)
```

##### 5.2.3 事务一致性（P1）
- **问题**：向量写入失败无补偿
- **方案**：添加 `indexing_status` 字段，失败标记重试
- **文件**：`app/models/chunk.py`, `app/services/ingestion.py`

##### 5.2.4 限流 Redis 化（P2）
- **问题**：多实例限流失效
- **方案**：Redis 滑动窗口
- **文件**：`app/auth/api_key.py`

##### 5.2.5 环境隔离（P2）
- **问题**：生产环境自动建表风险
- **方案**：`settings.environment` 判断
- **文件**：`app/main.py`

#### 5.3 开发任务
| 任务 | 优先级 | 复杂度 | 状态 |
|------|--------|--------|------|
| OpenAI Embedding 接入 | P0 | 中 | ✅ 已完成 |
| 异步化 Qdrant 客户端 | P0 | 中 | ✅ 已完成 |
| Chunk indexing_status | P1 | 低 | ✅ 已完成 |
| Redis 限流 | P2 | 中 | ✅ 已完成 |
| 环境隔离 init_models | P2 | 低 | ✅ 已完成 |

#### 5.4 已完成的修改

##### 5.4.1 Embedding 模块重构
- **文件**: `app/infra/embeddings.py`
- **变更**:
  - 新增 `get_embedding(text)` 异步函数，调用 OpenAI API
  - 新增 `get_embeddings(texts)` 批量异步函数
  - 新增 `deterministic_hash_embed()` 确定性哈希（MD5 替代 hash()）
  - 未配置 API Key 时自动降级到确定性哈希
  - 废弃 `hash_embed()`，保留兼容

##### 5.4.2 向量存储异步化
- **文件**: `app/infra/vector_store.py`
- **变更**:
  - 使用 `AsyncQdrantClient` 替代同步客户端
  - 所有方法改为 `async`：`upsert_chunk`, `upsert_chunks`, `search`, `delete_by_kb`
  - 新增批量 `upsert_chunks()` 方法提升写入效率
  - Collection 缓存避免重复检查

##### 5.4.3 调用方适配
- **文件**: `app/services/ingestion.py`
  - 使用批量 `await vector_store.upsert_chunks()`
- **文件**: `app/pipeline/retrievers/dense.py`
  - 改为 `await vector_store.search()`

##### 5.4.4 配置更新
- **文件**: `app/config.py`
  - 新增 `embedding_model` 配置（默认 `text-embedding-3-small`）
  - `embedding_dim` 默认改为 1536
  - 新增 `embedding_batch_size`
  - 新增 `redis_url` 配置
- **文件**: `app/main.py`
  - 生产环境跳过 `init_models()`

##### 5.4.5 Chunk 索引状态（P1）
- **文件**: `app/models/chunk.py`
  - 新增 `indexing_status` 字段（pending/indexing/indexed/failed）
  - 新增 `indexing_error` 字段（失败原因）
  - 新增 `indexing_retry_count` 字段（重试次数）
- **文件**: `app/services/ingestion.py`
  - 写入向量库前标记 `indexing` 状态
  - 成功后更新为 `indexed`，失败标记 `failed` 并记录错误
  - 新增 `retry_failed_chunks()` 函数用于重试

##### 5.4.6 Redis 限流（P2）
- **文件**: `app/auth/api_key.py`
  - 新增 `BaseRateLimiter` 抽象基类
  - 新增 `MemoryRateLimiter`（原有实现）
  - 新增 `RedisRateLimiter`（使用 Redis Sorted Set）
  - 新增 `get_rate_limiter()` 工厂函数，根据配置自动选择
  - 未配置 Redis 时自动降级到内存限流

---

### Phase 6：安全加固 ✅ 已完成（2024-12-08）

> 目标：修复权限和访问控制相关的安全漏洞，确保生产环境安全。

#### 6.1 发现的安全问题

| 问题 | 严重程度 | 文件 | 描述 |
|------|----------|------|------|
| **API Key 管理缺少角色校验** | 🔴 P0 高危 | `app/api/routes/api_keys.py` | 所有 Key 管理接口只验证 Key 有效，未检查 role，read 权限可创建 admin Key |
| **RAG 流程缺少 ACL 过滤** | 🔴 P0 高危 | `app/services/rag.py` | `retrieve_chunks` 未传 `user_context`，ACL 完全缺失，受限文档可被任意 Key 读取 |
| **/v1/rag 缺少 KB/scope 校验** | 🟠 P1 中危 | `app/api/routes/rag.py` | 未校验 KB 存在性和 `scope_kb_ids`，带 scope 的 Key 可查询任意 KB |
| **PermissionError 返回 500** | 🟡 P2 低危 | `app/api/routes/openai_compat.py` | ACL 被拒绝时返回 500 而非 403，客户端无法正确识别权限问题 |

#### 6.2 修复计划

##### 6.2.1 API Key 管理角色校验（P0）
- **问题**：`read` 权限的 Key 可以创建、撤销、轮转其他 Key，存在权限提升风险
- **方案**：为所有 API Key 管理接口添加 `require_role("admin")` 校验
- **文件**：`app/api/routes/api_keys.py`

```python
# 修复后
from app.api.deps import require_role

@router.post("/v1/api-keys", ...)
async def create_api_key(
    payload: APIKeyCreate,
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(require_role("admin")),  # 校验 admin 角色
    db: AsyncSession = Depends(get_db_session),
):
    ...
```

**影响范围**：
- `POST /v1/api-keys` - 创建 Key
- `GET /v1/api-keys` - 列出 Key（可保留 admin/write）
- `POST /v1/api-keys/{id}/revoke` - 撤销 Key
- `POST /v1/api-keys/{id}/rotate` - 轮转 Key
- `PATCH /v1/api-keys/{id}` - 更新 Key
- `DELETE /v1/api-keys/{id}` - 删除 Key

##### 6.2.2 RAG 流程 ACL 修复（P0）
- **问题**：`generate_rag_response` 调用 `retrieve_chunks` 时未传 `user_context`，导致 ACL 过滤缺失
- **方案**：从路由层传递 `api_key_ctx` 到 RAG 服务，构建 `UserContext` 进行 ACL 过滤
- **文件**：`app/services/rag.py`, `app/api/routes/rag.py`, `app/api/routes/openai_compat.py`

```python
# app/services/rag.py 修复后
async def generate_rag_response(
    *,
    session: AsyncSession,
    tenant_id: str,
    params: RAGParams,
    user_context: UserContext | None = None,  # 新增参数
) -> RAGResponse:
    ...
    chunks, retriever_name, acl_blocked = await retrieve_chunks(
        tenant_id=tenant_id,
        kbs=kbs,
        params=retrieve_params,
        session=session,
        user_context=user_context,  # 传入 ACL 上下文
    )
    ...
```

##### 6.2.3 /v1/rag KB 和 scope 校验（P1）
- **问题**：未验证请求的 KB 是否存在且属于租户，也未检查 `scope_kb_ids`
- **方案**：参照 `/v1/retrieve` 和 `/v1/chat/completions` 添加完整校验
- **文件**：`app/api/routes/rag.py`

```python
# 修复后
@router.post("/v1/rag", response_model=RAGResponse)
async def rag_generate(
    payload: RAGRequest,
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),  # 不再忽略
    db: AsyncSession = Depends(get_db_session),
):
    # 1. 校验 KB 存在性
    kbs = await get_tenant_kbs(db, tenant_id=tenant.id, kb_ids=payload.knowledge_base_ids)
    if len(kbs) != len(set(payload.knowledge_base_ids)):
        raise HTTPException(status_code=404, detail={"code": "KB_NOT_FOUND", ...})
    
    # 2. 校验 scope_kb_ids
    scope_kb_ids = api_key_ctx.api_key.scope_kb_ids
    if scope_kb_ids:
        unauthorized = set(payload.knowledge_base_ids) - set(scope_kb_ids)
        if unauthorized:
            raise HTTPException(status_code=403, detail={"code": "KB_NOT_IN_SCOPE", ...})
    
    # 3. 构建 user_context 传入 RAG
    user_context = api_key_ctx.get_user_context()
    ...
```

##### 6.2.4 OpenAI 兼容接口 PermissionError 处理（P2）
- **问题**：`PermissionError` 落入通用异常捕获，返回 500 而非 403
- **方案**：单独捕获 `PermissionError` 并映射到 403
- **文件**：`app/api/routes/openai_compat.py`

```python
# 修复后
try:
    rag_result = await generate_rag_response(...)
except PermissionError as e:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "NO_PERMISSION", "detail": str(e)},
    )
except HTTPException:
    raise
except Exception as e:
    logger.error(f"RAG 生成失败: {e}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "RAG_GENERATION_FAILED", "detail": str(e)},
    )
```

#### 6.3 开发任务

| 任务 | 优先级 | 复杂度 | 状态 |
|------|--------|--------|------|
| API Key 管理角色校验 | P0 | 低 | ✅ 已完成 |
| RAG 流程 ACL 传递 | P0 | 中 | ✅ 已完成 |
| /v1/rag KB/scope 校验 | P1 | 低 | ✅ 已完成 |
| OpenAI 接口 PermissionError | P2 | 低 | ✅ 已完成 |

#### 6.5 已完成的修改

##### 6.5.1 API Key 管理角色校验（P0）
- **文件**: `app/api/routes/api_keys.py`
- **变更**:
  - 所有 6 个 API Key 管理接口改用 `require_role("admin")` 依赖
  - 涉及接口：创建、列表、撤销、轮转、更新、删除 Key
  - 非 admin 角色调用时返回 403 Forbidden

##### 6.5.2 RAG 流程 ACL 传递（P0）
- **文件**: `app/services/rag.py`
- **变更**:
  - `generate_rag_response` 新增 `user_context` 参数
  - 调用 `retrieve_chunks` 时传入 `user_context` 进行 Security Trimming
  - 导入 `UserContext` 类型

##### 6.5.3 /v1/rag KB/scope 校验（P1）
- **文件**: `app/api/routes/rag.py`
- **变更**:
  - 添加 KB 存在性校验（`get_tenant_kbs`）
  - 添加 `scope_kb_ids` 白名单检查
  - 构建 `user_context` 并传入 RAG 服务
  - 原 `_` 变量改为 `api_key_ctx` 实际使用

##### 6.5.4 OpenAI 接口 PermissionError（P2）
- **文件**: `app/api/routes/openai_compat.py`
- **变更**:
  - 单独捕获 `PermissionError` 异常
  - ACL 被拒绝时返回 403 + `NO_PERMISSION` 错误码
  - 构建 `user_context` 并传入 RAG 服务

#### 6.4 测试验证

修复完成后需要验证：

```bash
# 1. 测试 read 角色不能管理 Key
curl -X POST "http://localhost:8020/v1/api-keys" \
  -H "Authorization: Bearer $READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "role": "admin"}'
# 期望: 403 Forbidden

# 2. 测试 RAG ACL 过滤
# 使用无权限的 Key 访问受限文档
curl -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer $LIMITED_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "knowledge_base_ids": ["kb_with_restricted_docs"]}'
# 期望: 403 NO_PERMISSION（如果所有结果被 ACL 过滤）

# 3. 测试 scope 限制
# 使用带 scope 的 Key 访问非授权 KB
curl -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer $SCOPED_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "knowledge_base_ids": ["unauthorized_kb"]}'
# 期望: 403 KB_NOT_IN_SCOPE
```

---

## 七、模型配置动态化

### 7.1 问题分析

**当前架构缺陷**：
- 模型配置（LLM/Embedding/Rerank）写死在环境变量
- 切换模型需要修改 `.env` 并**重启服务**
- 所有租户被迫使用**同一套模型**
- Docker 部署后**无法动态调整**

```
┌─────────────────────────────────────────────────┐
│  环境变量 (.env / Docker ENV)                    │
│  LLM_PROVIDER=ollama, LLM_MODEL=qwen3:14b       │
└───────────────────┬─────────────────────────────┘
                    ▼ 全局单例 (lru_cache)
┌─────────────────────────────────────────────────┐
│  get_settings() → Settings                      │
│  所有租户、所有KB、所有请求共用                    │
└─────────────────────────────────────────────────┘
```

### 7.2 目标架构

配置优先级：**请求级 > 知识库级 > 租户级 > 系统级 > 环境变量默认**

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

### 7.3 不同模型的配置策略

| 模型类型 | 配置层级 | 说明 |
|---------|---------|------|
| **Embedding** | 知识库级（固定） | 创建 KB 时确定，不可变（向量维度绑定） |
| **LLM** | 请求/租户/系统 | 动态切换，用于 HyDE/RAG 等 |
| **Rerank** | 请求/租户/系统 | 动态切换，检索后处理 |

### 7.4 数据模型设计

#### 7.4.1 系统配置表 (SystemConfig)

```python
# app/models/system_config.py
class SystemConfig(Base):
    """系统级配置（可通过 Admin API 修改，无需重启）"""
    __tablename__ = "system_configs"
    
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON 存储
    description: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime]
```

**预置配置项**：
| Key | 说明 | 示例值 |
|-----|------|--------|
| `llm_provider` | 默认 LLM 提供商 | `"ollama"` |
| `llm_model` | 默认 LLM 模型 | `"qwen3:14b"` |
| `embedding_provider` | 默认 Embedding 提供商 | `"ollama"` |
| `embedding_model` | 默认 Embedding 模型 | `"bge-m3"` |
| `embedding_dim` | 默认向量维度 | `1024` |
| `rerank_provider` | 默认 Rerank 提供商 | `"none"` |
| `rerank_model` | 默认 Rerank 模型 | `""` |

#### 7.4.2 租户模型配置扩展

```python
# Tenant 表新增字段
model_config: Mapped[dict | None] = mapped_column(JSON, default=dict)
# 示例:
# {
#   "llm_provider": "openai",
#   "llm_model": "gpt-4",
#   "rerank_provider": "cohere",
#   "rerank_model": "rerank-v3"
# }
```

#### 7.4.3 知识库 Embedding 配置

```python
# KnowledgeBase.config 结构
{
    "embedding_provider": "ollama",  # 创建时必须指定
    "embedding_model": "bge-m3",
    "embedding_dim": 1024,
    # ... 其他可变配置
}
```

### 7.5 配置解析服务

```python
# app/services/model_config.py
class ModelConfigResolver:
    """模型配置解析器 - 按优先级合并配置"""
    
    async def get_llm_config(
        self,
        session: AsyncSession,
        request_override: dict | None = None,
        tenant: Tenant | None = None,
    ) -> dict:
        """获取 LLM 配置（请求 > 租户 > 系统 > 环境变量）"""
        ...
    
    async def get_embedding_config(
        self,
        session: AsyncSession,
        kb: KnowledgeBase | None = None,
    ) -> dict:
        """获取 Embedding 配置（KB > 系统 > 环境变量）"""
        ...
    
    async def get_rerank_config(
        self,
        session: AsyncSession,
        request_override: dict | None = None,
        tenant: Tenant | None = None,
    ) -> dict:
        """获取 Rerank 配置（请求 > 租户 > 系统 > 环境变量）"""
        ...
```

### 7.6 Admin API

```
GET    /admin/system-config           - 获取所有系统配置
GET    /admin/system-config/{key}     - 获取单个配置
PUT    /admin/system-config/{key}     - 更新配置（立即生效）
POST   /admin/system-config/reset     - 重置为环境变量默认值
```

### 7.7 开发任务

| 任务 | 优先级 | 复杂度 | 状态 |
|------|--------|--------|------|
| SystemConfig 模型 + 迁移 | P0 | 低 | ✅ 已完成 |
| Tenant.llm_settings 字段扩展 | P0 | 低 | ✅ 已完成 |
| ModelConfigResolver 服务 | P0 | 中 | ✅ 已完成 |
| Admin API 系统配置管理 | P1 | 低 | ✅ 已完成 |
| infra 层改造（llm/embedding） | P2 | 中 | ✅ 已完成 |
| KB 创建时 Embedding 配置校验 | P2 | 低 | ✅ 已完成 |
| 请求级 LLM/Rerank 覆盖 | P2 | 低 | ✅ 已完成 |

### 7.8 兼容性设计

- 环境变量作为**默认值**，保持向后兼容
- 数据库配置**优先级更高**
- 未配置时自动降级到环境变量
- 配置变更**立即生效**，无需重启

---

## 八、技术选型（已确定）

| 组件 | 选型 |
|------|------|
| **向量库** | Qdrant（默认）/ Milvus / ES 可选 |
| **分块** | LlamaIndex NodeParser + 自定义扩展 |
| **检索** | LlamaIndex Retriever |
| **重排** | `BAAI/bge-reranker-base` |
| **Embedding** | 按配置，默认 OpenAI `text-embedding-3-small` |

---

## 八、前端入库流程优化 ✅ 已完成

> 目标：优化 Ground 入库流程的用户体验，实现快速响应和后台异步处理。

### 8.1 问题背景

**原有流程的问题**：
- 点击"创建并入库"后，前端显示进度对话框等待入库完成
- 大量文档入库时，用户需要长时间等待
- 无法在入库过程中查看已处理的文档

### 8.2 优化方案

**新流程（快速响应 + 后台入库）**：

```
用户点击"创建并入库"
    │
    ▼
后端 ingestGround API
    ├─ 1. 创建知识库
    ├─ 2. 为每个文档创建 Document 记录（状态: pending, chunk_count: 0）
    ├─ 3. 立即返回响应（包含 KB ID 和文档列表）
    └─ 4. 启动后台任务执行实际入库
    │
    ▼
前端收到响应后立即跳转到知识库详情页
    │
    ▼
知识库详情页
    ├─ 显示所有文档（包括处理中的）
    ├─ 处理中的文档显示加载动画
    ├─ 每 3 秒自动轮询刷新状态
    └─ 点击"查看日志"可查看详细入库进度
```

### 8.3 技术实现

#### 8.3.1 后端修改

**文件**: `app/api/routes/ground.py`

- `ingest_ground_to_kb` 函数重构：
  - 先验证 Embedding 配置
  - 为每个文档创建 `Document` 记录（`chunk_count=0`）
  - 使用 `asyncio.create_task` 启动后台任务
  - 立即返回响应

- 新增 `_background_ingest_documents` 函数：
  - 使用独立的数据库会话（`async_session_maker`）
  - 调用 `ingest_document` 进行实际入库
  - 更新文档的 `processing_log` 和状态

**文件**: `app/schemas/internal.py`

- `IngestionParams` 新增 `existing_doc_id` 字段，支持使用已存在的文档记录

**文件**: `app/services/ingestion.py`

- `ingest_document` 函数支持 `existing_doc_id` 参数
- 当传入已存在的文档 ID 时，跳过创建文档记录步骤

**文件**: `app/models/document.py`

- 新增 `processing_log` 字段，存储入库过程的详细日志

#### 8.3.2 前端修改

**文件**: `frontend/src/app/(main)/compare/[id]/page.tsx`

- `handleIngestToKb` 函数：
  - 调用 `ingestGround` API 并等待响应
  - 响应后立即跳转到知识库详情页
  - 显示成功提示

**文件**: `frontend/src/app/(main)/knowledge-bases/[id]/page.tsx`

- 文档列表显示"处理中"状态（当 `chunk_count === 0` 时）
- 自动轮询：当有处理中的文档时，每 3 秒刷新一次
- 查看日志弹窗显示 `processing_log` 详细内容

### 8.4 数据库迁移

新增 `processing_log` 字段：

```bash
uv run alembic revision --autogenerate -m "add document processing_log"
uv run alembic upgrade head
```

### 8.5 用户体验改进

| 改进点 | 原有体验 | 新体验 |
|--------|---------|--------|
| **响应速度** | 等待所有文档入库完成 | 立即跳转，秒级响应 |
| **进度可见** | 仅显示百分比 | 可查看每个文档的详细日志 |
| **状态感知** | 等待对话框 | 文件列表显示"处理中"状态 |
| **自动刷新** | 需手动刷新 | 自动轮询更新状态 |

### 8.6 日志实时更新机制

为了让前端能够实时显示入库进度，系统实现了日志实时保存和前端轮询机制。

#### 8.6.1 后端日志实时保存

**文件**: `app/services/ingestion.py`

入库过程中，每个步骤完成后会立即将日志保存到数据库：

```python
# 处理日志缓冲区
log_lines: list[str] = []
doc_ref: list = []  # 存储文档引用

async def save_log_to_db():
    """将日志实时保存到数据库（使用 commit 确保其他会话可见）"""
    if doc_ref:
        doc_ref[0].processing_log = "\n".join(log_lines)
        await session.commit()

async def add_step(step_num: int, total: int, label: str, status: str = "running"):
    """添加步骤进度信息并保存到数据库"""
    steps_info.append({"step": step_num, "total": total, "label": label, "status": status})
    add_log(f"[STEP:{step_num}/{total}:{status}] {label}")
    await save_log_to_db()  # 每个步骤后立即保存
```

**关键点**：
- 使用 `commit()` 而不是 `flush()`，确保其他数据库会话能看到更新
- 在使用已存在的文档记录时，先读取现有日志避免覆盖：
  ```python
  if doc.processing_log:
      log_lines.extend(doc.processing_log.split("\n"))
  ```

#### 8.6.2 API 响应包含日志字段

**文件**: `app/api/routes/documents.py`

获取文档详情 API 必须返回 `processing_log` 字段：

```python
return DocumentDetailResponse(
    id=doc.id,
    title=doc.title,
    # ... 其他字段
    processing_log=doc.processing_log,  # 必须包含此字段
)
```

#### 8.6.3 前端轮询机制

**文件**: `frontend/src/app/(main)/knowledge-bases/[id]/page.tsx`

当日志对话框打开且文档处理中时，前端每 2 秒自动刷新日志：

```typescript
// 日志对话框打开时自动轮询刷新（当文档处理中时）
useEffect(() => {
  if (!logDialogOpen || !logTarget?.id || !client) return;
  
  // 检查当前文档是否正在处理中
  const doc = documents.find(d => d.id === logTarget.id);
  const isProcessing = doc && doc.chunk_count === 0;
  
  if (!isProcessing) return;
  
  // 每 2 秒刷新一次日志
  const interval = setInterval(() => {
    fetchDocumentLog(logTarget.id);
  }, 2000);
  
  return () => clearInterval(interval);
}, [logDialogOpen, logTarget?.id, client, documents, fetchDocumentLog]);
```

#### 8.6.4 日志格式

入库日志采用结构化格式，便于前端解析和展示：

```
[2025-12-16 15:57:03] [INFO] 开始处理文档: 文档标题
[2025-12-16 15:57:03] [INFO] 使用已存在的文档记录: doc_id=xxx
[2025-12-16 15:57:03] [INFO] [STEP:1/6:running] 解析切分器配置
[2025-12-16 15:57:03] [INFO] 使用切分器: ParentChildChunker
[2025-12-16 15:57:03] [INFO] [STEP:1:done]
[2025-12-16 15:57:03] [INFO] [STEP:2/6:running] 创建文档记录
...
[2025-12-16 15:58:30] [INFO] 文档入库完成! 总耗时 87.5s, chunks=48
```

**步骤标识格式**：
- `[STEP:N/M:running]` - 步骤 N（共 M 步）开始执行
- `[STEP:N:done]` - 步骤 N 完成
- `[STEP:N:error]` - 步骤 N 出错

---

## 九、参考资料

- [R2R 项目](https://github.com/SciPhi-AI/R2R) - 分块和检索架构参考
- [LlamaIndex 文档](https://docs.llamaindex.ai/) - 核心框架
- R2R 分块实现：`/home/admin1/work/R2R/py/shared/utils/splitter/text.py`
