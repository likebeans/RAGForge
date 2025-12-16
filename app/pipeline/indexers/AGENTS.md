# Indexers 索引器模块

索引器用于在文档入库时构建高级索引结构，提升检索效果。

## 模块职责

- 构建多层次索引结构（如 RAPTOR 树）
- 索引持久化与加载
- 与入库流程（ingestion）集成

## 可用索引器

| 名称 | 类 | 说明 | 状态 |
|------|-----|------|------|
| `raptor` | `RaptorIndexer` | RAPTOR 多层次摘要树索引 | 🚧 开发中 |

## RAPTOR 索引器

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 是一种基于递归聚类和摘要的多层次索引方法。

**参考论文**：https://arxiv.org/abs/2401.18059

### 核心原理

```
                    RAPTOR 索引树结构
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Layer 3 (Root):      [Global Summary]                     │
│                            │                               │
│  Layer 2:          [Summary A]  [Summary B]                │
│                      /    \        /    \                  │
│  Layer 1:        [S1]    [S2]   [S3]   [S4]                │
│                   / \     |      |    /   \                │
│  Layer 0:      [C1][C2] [C3]   [C4] [C5] [C6]  (原始Chunks)│
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**构建流程**：
1. **切分**：将文档切分为原始 Chunks（Layer 0）
2. **向量化**：对所有 Chunks 生成向量表示
3. **聚类**：使用 GMM/K-Means 对相似 Chunks 分组
4. **摘要**：对每个聚类使用 LLM 生成摘要（Layer 1）
5. **递归**：将摘要作为新节点，重复步骤 3-4 直到达到最大层数

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llm` | LLM | None | LLM 实例，用于生成摘要 |
| `embed_model` | BaseEmbedding | None | Embedding 模型实例 |
| `vector_store` | VectorStore | None | 向量存储实例（可选，用于持久化） |
| `max_layers` | int | 3 | 最大层数（1-5） |
| `summary_num_workers` | int | 4 | 摘要生成并发数 |
| `summary_prompt` | str | None | 自定义摘要提示词 |

### 使用示例

```python
from app.pipeline.indexers.raptor import RaptorIndexer, create_raptor_indexer_from_config

# 从应用配置创建索引器
indexer = create_raptor_indexer_from_config()

# 从 chunks 构建索引
chunks = [
    {"text": "文本内容1...", "metadata": {"doc_id": "doc1"}},
    {"text": "文本内容2...", "metadata": {"doc_id": "doc1"}},
]
result = indexer.build_from_chunks(chunks)

print(f"总节点: {result.total_nodes}")
print(f"层数: {result.levels}")
print(f"叶子节点: {result.leaf_nodes}")
print(f"摘要节点: {result.summary_nodes}")

# 获取检索器
retriever = indexer.get_retriever(mode="collapsed", top_k=5)
results = retriever.retrieve("查询问题")
```

### 检索模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `collapsed` | 所有层级节点扁平化，统一 top-k 检索 | 速度快，通用场景 |
| `tree_traversal` | 从顶层开始，逐层向下筛选 | 更精确，长文档复杂查询 |

### 数据结构

```python
@dataclass
class RaptorNode:
    """RAPTOR 树节点"""
    id: str                      # 节点 ID
    text: str                    # 文本内容（原始或摘要）
    level: int                   # 层级（0=原始chunk, 1+=摘要层）
    children_ids: list[str]      # 子节点 ID 列表
    metadata: dict               # 元数据

@dataclass
class RaptorIndexResult:
    """索引构建结果"""
    total_nodes: int             # 总节点数
    levels: int                  # 层数
    leaf_nodes: int              # 叶子节点数（原始 chunks）
    summary_nodes: int           # 摘要节点数
    nodes: list[RaptorNode]      # 所有节点
```

### KB 配置

在知识库配置中启用 RAPTOR：

```json
{
  "raptor": {
    "enabled": true,
    "max_layers": 3,
    "cluster_method": "gmm",
    "min_cluster_size": 3,
    "summary_prompt": null
  }
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | false | 是否启用 RAPTOR 索引 |
| `max_layers` | int | 3 | 最大层数 |
| `cluster_method` | str | "gmm" | 聚类方法（gmm/kmeans） |
| `min_cluster_size` | int | 3 | 最小聚类大小 |
| `summary_prompt` | str | null | 自定义摘要提示词 |

### 实现状态

**当前版本**：
- [x] RaptorIndexer 基础框架（封装 LlamaIndex RaptorPack）
- [x] build_from_texts / build_from_chunks
- [x] get_retriever（collapsed/tree_traversal）
- [x] RaptorRetriever 占位符

**待开发**：
- [ ] 索引持久化（save/load）
- [ ] 入库集成（ingestion.py 调用）
- [ ] 检索集成（RaptorRetriever 加载索引）
- [ ] 数据模型（raptor_nodes 表）
- [ ] API 端点（构建/状态查询）
- [ ] 前端配置界面

### 技术依赖

```toml
# pyproject.toml
"llama-index-packs-raptor>=0.1.3"
```

### 注意事项

1. **LLM 成本**：RAPTOR 索引需要为每个聚类生成摘要，大文档会消耗大量 LLM Token
2. **构建时间**：索引构建可能耗时较长，建议异步后台执行
3. **增量更新**：当前版本不支持增量更新，新增文档需要重建整个索引
4. **向量一致性**：检索时必须使用与构建时相同的 Embedding 模型

## 添加新索引器

1. 在 `indexers/` 下创建新文件
2. 实现索引构建和检索接口
3. 在 `indexers/__init__.py` 中导出
4. 集成到 `ingestion.py` 入库流程
5. 更新 KB 配置 schema
