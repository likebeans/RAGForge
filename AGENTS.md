# AGENTS.md

本文档为 AI 编程助手提供项目上下文和开发指南。

## 项目概述

Self-RAG Pipeline 是一个多租户知识库检索服务，提供 OpenAI 兼容的 API 接口和完整的 Python SDK。

**核心功能**：
- 租户管理（创建、禁用、配额）
- 知识库管理（创建、删除）
- 文档摄取（上传、切分、向量化）
- 语义检索（向量/BM25/混合/Rerank）
- RAG 生成（多 LLM 提供商）
- API Key 认证与限流（角色权限）
- 可观测性（结构化日志、请求追踪）
- 审计日志（全链路访问记录）
- **OpenAI 兼容接口**（Embeddings、Chat Completions）
- **Python SDK**（完整的客户端库）

**技术栈**：
- Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async)
- PostgreSQL (元数据) / Qdrant (默认向量库) / 可选 Milvus、Elasticsearch
- LlamaIndex（chunk/retriever 适配）
- uv (依赖管理) / Alembic (数据库迁移)

## 开发环境

```bash
# 安装依赖
uv sync

# 启动基础设施（PostgreSQL + Qdrant + API）
docker compose up -d

# 运行数据库迁移
uv run alembic upgrade head

# 开发模式启动（本地端口 8020）
uv run uvicorn app.main:app --reload --port 8020
```

## 构建与测试

```bash
# 运行单元测试
uv run pytest tests/ -v

# 运行端到端测试（需要先启动服务）
API_KEY="your_key" API_BASE="http://localhost:8020" uv run pytest test/test_live_e2e.py

# 类型检查
uv run mypy app/

# 代码格式化
uv run ruff format .
uv run ruff check --fix .

# Docker 构建（使用宿主机网络加速）
docker build --network=host -t self_rag_pipeline-api .
```

## 项目结构

```
app/
├── main.py          # FastAPI 应用入口
├── config.py        # 配置管理（环境变量）
├── api/             # API 路由层
│   ├── deps.py      # 依赖注入（认证、数据库会话）
│   └── routes/      # 各功能路由
├── auth/            # 认证模块
│   └── api_key.py   # API Key 认证、限流
├── models/          # SQLAlchemy ORM 模型
├── schemas/         # Pydantic 请求/响应模型
├── pipeline/        # 可插拔算法模块
│   ├── base.py      # 基础协议定义
│   ├── registry.py  # 算法注册表
│   ├── chunkers/    # 切分器（simple/sliding_window/recursive/markdown/code 等）
│   ├── retrievers/  # 检索器（dense/bm25/hybrid/fusion/hyde 等）
│   ├── query_transforms/  # 查询变换（HyDE/Router/RAGFusion）
│   ├── enrichers/   # 文档增强（Summary/ChunkEnricher）
│   └── postprocessors/    # 后处理（ContextWindow）
├── middleware/      # 中间件
│   └── request_trace.py # 请求追踪（X-Request-ID）
├── infra/           # 基础设施
│   ├── llm.py           # LLM 客户端（多提供商支持）
│   ├── embeddings.py    # 向量化（多提供商支持）
│   ├── rerank.py        # 重排模块（多提供商支持）
│   ├── logging.py       # 结构化日志（JSON/Console）
│   ├── vector_store.py  # Qdrant 操作
│   ├── bm25_store.py    # BM25 内存存储
│   ├── llamaindex.py    # LlamaIndex 集成（Qdrant/Milvus/ES 构建器）
│   └── db/              # 异步会话管理
├── services/
│   ├── ingestion.py     # 文档摄取
│   ├── query.py         # 检索服务（含 Rerank 后处理）
│   ├── rag.py           # RAG 生成服务
│   ├── audit.py         # 审计日志服务
│   └── config_validation.py  # KB 配置校验
└── models/
    ├── audit_log.py     # 审计日志模型
    └── ...

sdk/                 # Python SDK
alembic/             # 数据库迁移脚本
tests/               # 测试文件
```

## Pipeline 算法框架

项目采用可插拔的算法框架，支持动态注册和发现算法组件。

### 切分器 (Chunkers)
- `simple`: 按段落切分
- `sliding_window`: 滑动窗口切分
- `parent_child`: 父子分块
- `recursive`: 递归字符切分（推荐通用文档）
- `markdown`: Markdown 感知切分（按标题层级）
- `code`: 代码感知切分（按语法结构）
- `llama_sentence`: LlamaIndex 句子切分
- `llama_token`: LlamaIndex Token 切分

### 检索器 (Retrievers)
- `dense`: 稠密向量检索
- `hybrid`: 混合检索（Dense + BM25，带 source 标记）
- `fusion`: 融合检索（RRF/加权 + 可选 Rerank）
- `hyde`: HyDE 检索器（LLM 生成假设文档嵌入）
- `multi_query`: 多查询扩展检索（LLM 生成查询变体，RRF 融合）
- `self_query`: 自查询检索（LLM 解析元数据过滤条件）
- `parent_document`: 父文档检索（小块检索返回父块上下文）**需要 `parent_child` 切分器**
- `ensemble`: 集成检索（任意组合多检索器）
- `llama_dense`: LlamaIndex 稠密检索（真实 Embedding）
- `llama_bm25`: LlamaIndex BM25 检索（从 DB 加载）
- `llama_hybrid`: LlamaIndex 混合检索
- `raptor`: RAPTOR 多层次索引检索（递归聚类+摘要树）**需要 RAPTOR 索引**

#### 检索器兼容性要求

部分检索器对知识库配置有特殊要求：

| 检索器 | 要求 | 说明 |
|--------|------|------|
| `raptor` | RAPTOR 索引 | 需要在入库时启用 RAPTOR 索引增强 |
| `parent_document` | `parent_child` 切分器 | 需要使用父子分块切分器入库 |

前端检索对比页面会自动检测知识库配置，对不兼容的检索器显示警告。

### 查询增强 (Query Transforms)
- `HyDEQueryTransform`: 假设文档嵌入查询变换
- `QueryRouter`: 查询路由，自动选择检索策略
- `RAGFusionTransform`: 多查询扩展

### 文档增强 (Enrichers)

文档增强用于在入库前为文档或 Chunk 添加额外的上下文信息，提升检索效果。

#### DocumentSummarizer - 文档摘要生成

对整个文档生成全局摘要，提供文档的整体上下文。

**配置选项**：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `summary_length` | 摘要长度（short/medium/long） | medium |
| `prepend_summary` | 是否将摘要前置到每个 chunk | true |

**前置摘要开关**：
| 状态 | 摘要存储位置 | Chunk 内容 |
|------|-------------|-----------|
| **开启** | 每个 chunk 开头 + 文档元数据 | `[摘要] + [原文]` |
| **关闭** | 仅文档元数据 | `[原文]`（不变） |

**开启前置摘要时**，每个 chunk 在入库时会变成：
```
[文档摘要]
该文档为健康科技有限公司关于胃肠道益生菌产品的研发项目报告...

[原始 Chunk 内容]
## 1. 项目背景
消费者以25-45岁都市白领为主...
```

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

### 后处理 (Postprocessors)
- `ContextWindowExpander`: 上下文窗口扩展

### 索引器 (Indexers)

#### RAPTOR 索引器

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 是一种多层次索引方法，通过递归聚类和摘要构建树状索引结构。

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

**KB 配置示例**：
```json
{
  "raptor": {
    "enabled": true,
    "max_layers": 3,
    "cluster_method": "gmm",
    "min_cluster_size": 3
  }
}
```

**实现状态**：🚧 开发中
- [x] RaptorIndexer 基础框架（封装 LlamaIndex RaptorPack）
- [x] RaptorRetriever 占位符
- [ ] 索引持久化（save/load）
- [ ] 入库集成（ingestion.py）
- [ ] 检索集成（从 KB 加载索引）
- [ ] 数据模型（raptor_nodes 表）

**参考论文**：https://arxiv.org/abs/2401.18059

### 使用示例
```python
from app.pipeline import operator_registry

# 获取切分器
chunker = operator_registry.get("chunker", "sliding_window")(window=512, overlap=100)
pieces = chunker.chunk("长文本...")

# 获取检索器
retriever = operator_registry.get("retriever", "hybrid")()
results = await retriever.retrieve(query="问题", tenant_id="xxx", kb_ids=["kb1"], top_k=5)
```

## 代码规范

- **注释语言**：中文注释，便于团队阅读
- **类型提示**：所有函数必须有类型标注
- **异步优先**：数据库和 HTTP 操作使用 async/await
- **ORM 字段命名**：避免使用 `metadata`（SQLAlchemy 保留字），使用 `extra_metadata` 并显式指定列名
- **错误处理**：使用 HTTPException 返回标准错误格式

## 多租户设计

- 每个请求通过 API Key 识别租户
- 所有数据表包含 `tenant_id` 字段
- 向量库按租户隔离（支持多种隔离策略）
- 查询时强制过滤 `tenant_id`
- 租户可被禁用，禁用后所有 API Key 失效

### 向量存储隔离模式

系统支持三种多租户隔离策略，通过环境变量或前端设置页面配置：

| 模式 | Collection 名称 | 隔离方式 | 适用场景 |
|------|----------------|---------|---------|
| **Partition** | `kb_shared` | 通过 `kb_id` 字段过滤 | 小规模、资源共享（默认） |
| **Collection** | `kb_{tenant_id}` | 每租户独立 Collection | 大规模、高性能需求 |
| **Auto** | 自动选择 | 根据数据量自动切换 | 自动优化、平衡成本 |

**配置方式**：
- 后端环境变量：`QDRANT_ISOLATION_STRATEGY`（partition/collection/auto）
- 前端设置页面：**设置 → 向量存储** Tab

**注意事项**：
1. 切换模式不会自动迁移已有数据
2. 入库和检索必须使用相同的隔离模式
3. 默认使用 Partition 模式（共享 Collection `kb_shared`）

## 租户管理 (Admin API)

通过 `X-Admin-Token` 头认证的管理接口：

```bash
# 配置管理员 Token
export ADMIN_TOKEN=your-secure-token

# 创建租户（返回初始 admin API Key）
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-company"}'

# 禁用租户
curl -X POST http://localhost:8020/admin/tenants/{id}/disable \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Payment overdue"}'
```

### Admin API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/tenants` | 创建租户 |
| GET | `/admin/tenants` | 列出租户 |
| GET | `/admin/tenants/{id}` | 租户详情 |
| PATCH | `/admin/tenants/{id}` | 更新租户 |
| POST | `/admin/tenants/{id}/disable` | 禁用租户 |
| POST | `/admin/tenants/{id}/enable` | 启用租户 |
| DELETE | `/admin/tenants/{id}` | 删除租户 |
| GET | `/admin/tenants/{id}/api-keys` | 列出 API Keys |
| POST | `/admin/tenants/{id}/api-keys` | 创建 API Key |

## API Key 角色权限

| 角色 | 说明 |
|------|------|
| `admin` | 全部权限 + 管理 API Key |
| `write` | 创建/删除 KB、上传文档、检索 |
| `read` | 仅检索和列表 |

## 常见问题

### 端口配置
- API 服务：8020（compose 映射 8020:8020）
- PostgreSQL：5435（宿主机）/ 5432（容器内）
- Qdrant：6333

### 数据库连接
- 本地开发：`postgresql+asyncpg://kb:kb@localhost:5435/kb`
- 容器内部：`postgresql+asyncpg://kb:kb@db:5432/kb`

### 添加新模型
1. 在 `app/models/` 创建模型文件
2. 在 `app/models/__init__.py` 导出
3. 运行 `uv run alembic revision --autogenerate -m "描述"`
4. 检查生成的迁移脚本后执行 `uv run alembic upgrade head`

## 模型提供商配置

支持多种 LLM/Embedding/Rerank 提供商：

| 提供商 | LLM | Embedding | Rerank |
|--------|-----|-----------|--------|
| Ollama | ✅ | ✅ | ✅ |
| OpenAI | ✅ | ✅ | - |
| Gemini | ✅ | ✅ | - |
| Qwen | ✅ | ✅ | - |
| Kimi | ✅ | - | - |
| DeepSeek | ✅ | ✅ | - |
| 智谱 AI | ✅ | ✅ | ✅ |
| SiliconFlow | ✅ | ✅ | ✅ |
| Cohere | - | - | ✅ |
| vLLM | ✅ | ✅ | ✅ |

配置示例：
```bash
# LLM
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:14b

# Embedding
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024

# Rerank (可选)
RERANK_PROVIDER=none
```

## 安全注意事项

- API Key 使用 SHA256 哈希存储，不保存明文
- 所有接口需要 Bearer Token 认证
- 限流器默认 120 次/分钟，可按 Key 独立配置
- 生产环境应启用 HTTPS

## 检索响应格式

检索接口 (`POST /v1/retrieve`) 返回模型配置信息：

```json
{
  "results": [
    {
      "chunk_id": "xxx",
      "text": "检索到的文本...",
      "score": 0.85,
      "metadata": {...},
      "knowledge_base_id": "kb_id",
      "hyde_queries": ["LLM生成的假设文档..."]
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "rerank_provider": null,
    "rerank_model": null,
    "retriever": "hyde"
  }
}
```

- `model.llm_*`: 仅 hyde/multi_query/self_query 检索器返回
- `model.rerank_*`: 仅 fusion 检索器且启用 rerank 时返回
- `hyde_queries`: HyDE 检索器返回 LLM 生成的假设文档
- `semantic_query`: Self-Query 检索器返回 LLM 提取的语义查询
- `parsed_filters`: Self-Query 检索器返回 LLM 解析的元数据过滤条件
- `generated_queries`: Multi-Query 检索器返回 LLM 生成的查询变体

**Rerank 后可视化字段保留**：当启用 Rerank 时，`hyde_queries`、`semantic_query`、`parsed_filters`、`generated_queries` 等可视化字段会自动从原始第一个结果迁移到 Rerank 后的第一个结果，确保前端可视化正常显示

## RAPTOR 索引器

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 是一种多层次索引方法。

### 原理

1. 将文档切分为 chunks
2. 对 chunks 进行向量聚类
3. 对每个聚类使用 LLM 生成摘要
4. 递归处理摘要，直到达到最大层数

### 使用示例

```python
from app.pipeline.indexers.raptor import create_raptor_indexer_from_config

# 创建索引器
indexer = create_raptor_indexer_from_config()

# 从文本构建索引
result = indexer.build_from_texts([
    "文档1内容...",
    "文档2内容...",
])
print(f"总节点: {result.total_nodes}, 层数: {result.levels}")

# 检索
retriever = indexer.get_retriever(mode="collapsed", top_k=5)
results = retriever.retrieve("查询问题")
for r in results:
    print(f"[Level {r['raptor_level']}] {r['text'][:50]}...")
```

### 检索模式

- `collapsed`: 扁平化检索，所有层级节点一起 top-k（默认）
- `tree_traversal`: 树遍历检索，从顶层向下逐层筛选

### 返回字段

- `raptor_level`: 节点层级（-1=原始文档，0/1/2=摘要层级）

### 依赖

```toml
# pyproject.toml
"llama-index-packs-raptor>=0.1.3"
"llama-index-llms-ollama>=0.1.0"
"llama-index-embeddings-ollama>=0.1.0"
```

---

## OpenAI 兼容接口与 Python SDK

项目提供完整的 OpenAI 兼容 API 和 Python SDK，详见：

- **详细文档**: `AGENTS_OPENAI_SDK.md`
- **SDK 文档**: `sdk/README.md`
- **测试脚本**: `test_openai_sdk.py`
- **测试总结**: `docs/OpenAI接口和SDK测试总结.md`

### 快速示例

```python
from kb_service_sdk import KBServiceClient

client = KBServiceClient(api_key="kb_sk_xxx", base_url="http://localhost:8020")

# OpenAI 兼容接口
response = client.openai.chat_completions(
    messages=[{"role": "user", "content": "Python 有什么应用？"}],
    model="gpt-4",
    knowledge_base_ids=["kb1"]  # 启用 RAG
)
```

---

## 待开发项 (TODO)

### Playground 后端持久化

**当前状态**：Playground（RAG Pipeline 对比实验）数据存储在浏览器 localStorage，仅适合本地演示。

**待开发内容**：

1. **数据库模型** (`app/models/playground.py`)
   - `Playground` 表：id, tenant_id, name, description, cover_id, created_at, updated_at
   - `PlaygroundConfig` 表：id, playground_id, name, chunker, chunk_size, chunk_overlap, retriever, top_k, embedding_provider, embedding_model, rerank_provider, vector_db, index_type

2. **API 路由** (`app/api/routes/playground.py`)
   - `POST /v1/playgrounds` - 创建 Playground
   - `GET /v1/playgrounds` - 列出当前租户的 Playground
   - `GET /v1/playgrounds/{id}` - 获取详情（含配置列表）
   - `PUT /v1/playgrounds/{id}` - 更新名称/描述
   - `DELETE /v1/playgrounds/{id}` - 删除
   - `POST /v1/playgrounds/{id}/configs` - 添加配置
   - `PUT /v1/playgrounds/{id}/configs/{config_id}` - 更新配置
   - `DELETE /v1/playgrounds/{id}/configs/{config_id}` - 删除配置

3. **前端改造** (`frontend/src/app/(main)/compare/`)
   - 列表页改为调用 `client.listPlaygrounds()`
   - 详情页改为调用 `client.getPlayground(id)` 和 `client.updatePlaygroundConfigs()`
   - 移除 localStorage 相关代码

4. **SDK 扩展** (`sdk/kb_service_sdk/`)
   - 添加 Playground 相关方法
