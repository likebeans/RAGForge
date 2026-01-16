# AGENTS.md

本文档为 AI 编程助手提供项目上下文和开发指南。

## 项目概述

**RAGForge** 是一个企业级多租户知识库检索服务，提供 OpenAI 兼容的 API 接口和完整的 Python SDK。

**核心功能**：
- 多租户架构（租户隔离、配额管理、权限控制）
- 知识库管理（创建、配置、删除）
- 文档摄取（上传、切分、向量化、索引）
- 语义检索（Dense/BM25/Hybrid/RAPTOR/HyDE 等）
- RAG 生成（多 LLM 提供商支持）
- 三层权限模型（操作权限 + KB 范围 + 文档 ACL）
- Security Trimming（检索时自动过滤无权限文档）
- 可观测性（结构化日志、请求追踪、审计日志）
- **OpenAI 兼容接口**（Embeddings、Chat Completions）
- **Python SDK**（完整的客户端库）
- **凭据管理**（主备密钥、自动故障切换、密钥轮换）
- **凭据扫描**（Pre-commit 钩子检测硬编码密钥）

**技术栈**：
- Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async)
- PostgreSQL + pgvector (默认向量库) / 可选 Qdrant、Milvus、Elasticsearch
- OpenSearch (BM25 稀疏检索)
- LlamaIndex（chunk/retriever 适配）
- uv (依赖管理) / Alembic (数据库迁移)

## 部署方式

项目提供两种部署配置：

| 配置 | 向量存储 | BM25 存储 | 适用场景 |
|------|----------|-----------|----------|
| **默认** (`docker-compose.yml`) | PostgreSQL pgvector | OpenSearch | 生产环境、大规模数据 |
| **Qdrant** (`docker-compose.qdrant.yml`) | Qdrant | 内存 | 开发环境、轻量部署 |

### 快速启动（推荐）

```bash
# 生产环境（pg + opensearch）
./deploy.sh up

# 开发环境（pg + qdrant）
./deploy.sh up qdrant

# 其他命令
./deploy.sh status          # 查看状态
./deploy.sh logs            # 查看日志
./deploy.sh create-tenant   # 创建租户
./deploy.sh backup          # 备份数据库
```

### 手动启动

```bash
# 生产环境
docker compose up -d
docker compose exec api uv run alembic upgrade head

# 开发环境
docker compose -f docker-compose.qdrant.yml up -d
docker compose -f docker-compose.qdrant.yml exec api uv run alembic upgrade head
```

### 本地开发

```bash
# 安装依赖
uv sync

# 仅启动基础服务
docker compose up -d db redis opensearch

# 运行数据库迁移
uv run alembic upgrade head

# 本地启动 API（热重载）
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
docker build --network=host -t ragforge-api .
```

## 项目结构

```
RAGForge/
├── app/                      # 应用代码
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理（环境变量）
│   ├── api/                 # API 路由层
│   │   ├── deps.py          # 依赖注入（认证、数据库会话）
│   │   └── routes/          # 各功能路由
│   ├── auth/                # 认证模块
│   │   └── api_key.py       # API Key 认证、限流
│   ├── security/            # 安全模块
│   │   ├── credential_manager.py   # 凭据管理器
│   │   └── credential_scanner.py   # 凭据扫描器
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 业务逻辑层
│   │   ├── ingestion.py     # 文档摄取
│   │   ├── query.py         # 检索服务
│   │   ├── rag.py           # RAG 生成服务
│   │   ├── acl.py           # ACL 权限服务
│   │   └── audit.py         # 审计日志服务
│   ├── pipeline/            # 可插拔算法模块
│   │   ├── base.py          # 基础协议定义
│   │   ├── registry.py      # 算法注册表
│   │   ├── chunkers/        # 切分器
│   │   ├── retrievers/      # 检索器
│   │   ├── indexers/        # 索引器（RAPTOR）
│   │   ├── query_transforms/  # 查询变换
│   │   ├── enrichers/       # 文档增强
│   │   └── postprocessors/  # 后处理
│   ├── infra/               # 基础设施
│   │   ├── llm.py           # LLM 客户端
│   │   ├── embeddings.py    # 向量化
│   │   ├── rerank.py        # 重排模块
│   │   ├── logging.py       # 结构化日志
│   │   ├── vector_store.py  # Qdrant 操作
│   │   ├── bm25_store.py    # BM25 存储
│   │   └── llamaindex.py    # LlamaIndex 集成
│   ├── middleware/          # 中间件
│   │   ├── audit.py         # 审计日志
│   │   └── request_trace.py # 请求追踪
│   └── db/                  # 数据库配置
├── frontend/                # Next.js 前端管理界面
├── sdk/                     # Python SDK
├── alembic/                 # 数据库迁移脚本
├── scripts/                 # 运维脚本
├── tests/                   # 测试文件
├── docs/                    # VitePress 文档站点
└── .pre-commit-config.yaml  # Pre-commit 配置
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

**实现状态**：✅ 可用
- [x] RaptorIndexer 基础框架（封装 LlamaIndex RaptorPack）
- [x] 入库集成（ingestion.py Step 6）
- [x] 数据模型（raptor_nodes 表）
- [x] 索引持久化（保存到 PostgreSQL）
- [x] 多提供商 Embedding（qwen/siliconflow/zhipu 等）
- [ ] RaptorRetriever 检索集成

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

### PostgreSQL pgvector 索引类型

使用 PostgreSQL pgvector 作为向量存储时，系统使用 **HNSW 索引**，并根据向量维度自动选择合适的类型：

| 向量类型 | 维度限制 | 适用场景 | 操作符类 |
|----------|----------|----------|----------|
| `vector` | ≤2,000 | 低维度模型（768/1024 维） | `vector_cosine_ops` |
| `halfvec` ✅ | ≤4,000 | **高维度模型（2560/3072 维）** | `halfvec_cosine_ops` |
| `bit` | ≤64,000 | 二进制向量 | `bit_cosine_ops` |

**自动索引策略**：
- 维度 ≤ 2000：使用 `vector` 类型 + `vector_cosine_ops`
- 维度 2001-4000：使用 `halfvec` 类型 + `halfvec_cosine_ops`
- 维度 > 4000：跳过索引（使用精确搜索）

**索引示例**：
```sql
-- 低维度向量（≤2000 维）
CREATE INDEX ON vector_chunks 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- 高维度向量（2001-4000 维，如 Qwen3-Embedding-4B 的 2560 维）
CREATE INDEX ON vector_chunks 
USING hnsw ((embedding::halfvec(2560)) halfvec_cosine_ops) WITH (m = 16, ef_construction = 64);
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `m` | 每个节点的最大连接数 | 16 |
| `ef_construction` | 构建时的搜索宽度 | 64 |

**参考文档**：[Supabase HNSW Indexes](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes)

**注意**：更高的 `m` 和 `ef_construction` 值会提高召回率，但增加内存和构建时间。

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

## 安全特性

### 基础安全
- API Key 使用 SHA256 哈希存储，不保存明文
- 所有接口需要 Bearer Token 认证
- 限流器默认 120 次/分钟，可按 Key 独立配置
- 生产环境应启用 HTTPS

### 凭据管理器 (CredentialManager)

提供完整的 API 密钥管理能力（`app/security/credential_manager.py`）：

- **主备密钥机制** - 每个提供商可配置主密钥和备用密钥
- **自动故障切换** - 主密钥失效时自动切换到备用密钥
- **密钥轮换** - 支持无缝轮换 API 密钥
- **密钥验证** - 自动验证密钥格式（OpenAI sk-、Gemini AIzaSy 等）

```python
from app.security.credential_manager import CredentialManager

manager = CredentialManager(settings)
api_key = manager.get_api_key("openai")  # 自动主备切换
manager.mark_key_invalid("openai")  # 标记失效，触发切换
await manager.rotate_key("openai", "new-key")  # 轮换密钥
```

### 凭据扫描器 (CredentialScanner)

自动检测代码中的硬编码凭据（`app/security/credential_scanner.py`）：

- **检测模式** - API 密钥、通用密码、弱令牌、内网 IP
- **Pre-commit 集成** - 提交前自动扫描，防止密钥泄露
- **白名单机制** - 支持 `.secrets.baseline` 配置已知安全例外

```bash
# 安装并启用 pre-commit
pip install pre-commit
pre-commit install

# 手动运行扫描
python scripts/pre-commit-security-check.py --all
```

详细信息参见 `docs/SECURITY.md`。

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

- **使用指南**: `docs/guides/openai-sdk.md`
- **SDK 文档**: `sdk/README.md`
- **测试报告**: `docs/reports/openai-sdk-testing.md`

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

---

## 文档资源

项目提供完整的 VitePress 文档站点（`docs/` 目录）：

| 分类 | 说明 | 路径 |
|------|------|------|
| **快速开始** | 安装、配置、第一个 API 调用 | `docs/getting-started/` |
| **使用指南** | 环境配置、部署、SDK 使用 | `docs/guides/` |
| **架构设计** | 系统设计、Pipeline 架构、API 规范 | `docs/architecture/` |
| **开发文档** | 贡献指南、测试、故障排查 | `docs/development/` |
| **运维文档** | 部署、监控、安全 | `docs/operations/` |
| **安全指南** | 凭据管理、威胁模型、审计 | `docs/SECURITY.md` |

### 关键文档

- **[docs/documentation.md](docs/documentation.md)** - 完整文档索引
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 系统架构概览
- **[docs/SECURITY.md](docs/SECURITY.md)** - 安全基线与加固建议
- **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)** - 贡献指南
