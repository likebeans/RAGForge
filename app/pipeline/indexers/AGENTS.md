# Indexers 索引器模块

索引器用于在文档入库时构建高级索引结构，提升检索效果。

## 模块职责

- 构建多层次索引结构（如 RAPTOR 树）
- 索引持久化与加载
- 与入库流程（ingestion）集成

## 可用索引器

| 名称 | 类 | 说明 | 状态 |
|------|-----|------|------|
| `raptor` | `RaptorNativeIndexer` | RAPTOR 多层次摘要树索引（原生实现） | ✅ 可用 |

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
from app.pipeline.indexers.raptor import (
    RaptorNativeIndexer,
    create_raptor_native_indexer_from_config,
)

# 从应用配置创建索引器（异步）
indexer = await create_raptor_native_indexer_from_config(
    embedding_config={"provider": "qwen", "model": "text-embedding-v3"},
    llm_config={"provider": "qwen", "model": "qwen-plus"},
)

# 从 chunks 构建索引（异步）
chunks = [
    {"text": "文本内容1...", "metadata": {"doc_id": "doc1"}},
    {"text": "文本内容2...", "metadata": {"doc_id": "doc1"}},
]
result = await indexer.build(chunks)

print(f"总节点: {result.total_nodes}")
print(f"层数: {result.levels}")
print(f"叶子节点: {result.leaf_nodes}")
print(f"摘要节点: {result.summary_nodes}")

# 保存到数据库和向量库
await indexer.save_to_vector_store(tenant_id, kb_id)
await indexer.save_to_db(session, tenant_id, kb_id, chunk_id_mapping)
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

**已完成**：
- [x] RaptorNativeIndexer 原生实现（参考 RAGFlow）
- [x] UMAP 降维 + GMM 聚类 + LLM 摘要
- [x] 异步 build() 方法
- [x] 入库集成（ingestion.py 调用，Step 6）
- [x] 数据模型（raptor_nodes 表）
- [x] 索引持久化（保存节点到 PostgreSQL + Qdrant）
- [x] 多提供商 Embedding 支持（qwen/siliconflow/zhipu/deepseek/kimi/gemini）
- [x] 正确设置 level 和 indexing_status
- [x] tree_traversal 检索模式
- [x] collapsed 检索模式

**待开发**：
- [ ] 前端配置界面

### 已实现功能

#### API 端点 ✅
RAPTOR 索引管理 API，支持手动构建、状态查询和删除：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/knowledge-bases/{kb_id}/raptor/status` | 查询索引状态 |
| POST | `/v1/knowledge-bases/{kb_id}/raptor/build` | 手动触发构建 |
| DELETE | `/v1/knowledge-bases/{kb_id}/raptor` | 删除索引 |

**状态响应示例**：
```json
{
  "has_index": true,
  "total_nodes": 42,
  "leaf_nodes": 30,
  "summary_nodes": 12,
  "max_level": 2,
  "nodes_by_level": [
    {"level": 0, "count": 30},
    {"level": 1, "count": 10},
    {"level": 2, "count": 2}
  ],
  "last_build_time": "2024-12-17T10:30:00Z",
  "indexing_status": "indexed"
}
```

#### tree_traversal 检索模式 ✅
从最高层摘要开始，逐层向下筛选，最终返回叶子节点：

```
Query → Layer 2 检索 → 选中 [Summary A, Summary B]
      → Layer 1 检索（仅子节点）→ 选中 [S1, S3]
      → Layer 0 检索（仅子节点）→ 返回 [C1, C2, C4]
```

**实现细节**：
1. 加载完整的 RAPTOR 树结构
2. 获取查询向量
3. 从最高层开始，对候选节点计算余弦相似度
4. 每层选择 top-k 节点，向下遍历其子节点
5. 最终返回叶子节点（原始 chunks）

#### 摘要→原文映射 ✅
当 collapsed 模式检索到摘要节点时，自动回溯返回对应的原始 chunks：
```
Query → 匹配到 Summary A (level=2) → 通过 children_ids 找到 [S1, S2] → 继续回溯 → 返回 [C1, C2, C3]
```

**实现细节**：
1. 检测检索结果中的摘要节点（level > 0）
2. 递归查找所有子孙叶子节点
3. 返回原始 chunks，同时保留摘要上下文
4. 通过 `expand_to_leaves` 参数控制是否展开（默认 True）

**扩展字段**：
```python
{
    "raptor_expanded_from": str,      # 展开来源的摘要节点 ID
    "raptor_summary_preview": str,    # 摘要内容预览（前100字符）
}
```

### 技术依赖

```toml
# pyproject.toml
"umap-learn>=0.5.0"      # UMAP 降维
"scikit-learn>=1.3.0"    # GMM 聚类
```

### 构建日志示例

以下是一个典型的 RAPTOR 索引构建日志：

```
[RAPTOR-Native] 开始构建索引: kb=278f42d7-xxx, chunks=48
[RAPTOR-Native] Step 1: 向量化 chunks...
[RAPTOR-Native] Step 1 完成: 向量化了 48 个 chunks
[RAPTOR-Native] Step 2.1: 处理 Layer 1...
[RAPTOR-Native] Layer 1: 最优聚类数 = 10
[RAPTOR-Native] Layer 1: 生成了 10 个摘要节点
[RAPTOR-Native] Step 2.2: 处理 Layer 2...
[RAPTOR-Native] Layer 2: 最优聚类数 = 3
[RAPTOR-Native] Layer 2: 生成了 3 个摘要节点
[RAPTOR-Native] Step 2.3: 处理 Layer 3...
[RAPTOR-Native] Layer 3: UMAP 降维失败: Cannot use scipy.linalg.eigh...
[RAPTOR-Native] RAPTOR 索引构建完成! 总节点 61, 层数 3, 叶子节点 48, 摘要节点 13
```

### 常见警告说明

构建过程中可能出现以下警告，均为**预期行为**，不影响最终结果：

| 警告 | 原因 | 影响 |
|------|------|------|
| `n_jobs value 1 overridden to 1 by setting random_state` | UMAP 设置了随机种子以保证结果可复现，强制单线程运行 | ⚪ 无影响，可忽略 |
| `k >= N for N * N square matrix` | 当前层节点数太少，UMAP 需要的特征向量数量 >= 数据点数量 | 🟡 UMAP 自动降级处理 |
| `Layer X: UMAP 降维失败` | 节点数太少（如只有3个），无法进行有效的降维聚类 | 🟢 预期行为，自动跳过该层 |

**Layer 聚类停止条件**：
- 当某层节点数少于 `min_cluster_size`（默认3）时，无法继续聚类
- 这是 RAPTOR 算法的正常收敛行为，表示已达到合理的抽象层级

### 注意事项

1. **LLM 成本**：RAPTOR 索引需要为每个聚类生成摘要，大文档会消耗大量 LLM Token
2. **构建时间**：索引构建可能耗时较长，建议异步后台执行
3. **增量更新**：当前版本不支持增量更新，新增文档需要重建整个索引
4. **向量一致性**：检索时必须使用与构建时相同的 Embedding 模型
5. **numpy 类型转换**：保存到数据库和向量库时，所有 numpy 类型会自动转换为原生 Python 类型

## 添加新索引器

1. 在 `indexers/` 下创建新文件
2. 实现索引构建和检索接口
3. 在 `indexers/__init__.py` 中导出
4. 集成到 `ingestion.py` 入库流程
5. 更新 KB 配置 schema
