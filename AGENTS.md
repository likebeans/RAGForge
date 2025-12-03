# AGENTS.md

本文档为 AI 编程助手提供项目上下文和开发指南。

## 项目概述

Self-RAG Pipeline 是一个多租户知识库检索服务，提供 OpenAI 兼容的 API 接口。

**核心功能**：
- 租户管理（创建、禁用、配额）
- 知识库管理（创建、删除）
- 文档摄取（上传、切分、向量化）
- 语义检索（向量/BM25/混合）
- API Key 认证与限流（角色权限）

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
├── services/        # 业务逻辑层
│   ├── ingestion.py # 文档摄取
│   └── query.py     # 检索服务
├── pipeline/        # 可插拔算法模块
│   ├── base.py      # 基础协议定义
│   ├── registry.py  # 算法注册表
│   ├── chunkers/    # 切分器（simple/sliding_window/recursive/markdown/code 等）
│   ├── retrievers/  # 检索器（dense/bm25/hybrid/fusion/hyde 等）
│   ├── query_transforms/  # 查询变换（HyDE/Router/RAGFusion）
│   ├── enrichers/   # 文档增强（Summary/ChunkEnricher）
│   └── postprocessors/    # 后处理（ContextWindow）
├── infra/           # 基础设施
│   ├── llm.py           # LLM 客户端（多提供商支持）
│   ├── embeddings.py    # 向量化（多提供商支持）
│   ├── rerank.py        # 重排模块（多提供商支持）
│   ├── vector_store.py  # Qdrant 操作
│   ├── bm25_store.py    # BM25 内存存储
│   ├── llamaindex.py    # LlamaIndex 集成（Qdrant/Milvus/ES 构建器）
│   └── db/              # 异步会话管理
└── services/config_validation.py  # KB 配置校验

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
- `bm25`: BM25 稀疏检索（从 DB 加载，支持持久化）
- `hybrid`: 混合检索（Dense + BM25，带 source 标记）
- `fusion`: 融合检索（RRF/加权 + 可选 Rerank）
- `hyde`: HyDE 检索器（LLM 生成假设文档嵌入）
- `multi_query`: 多查询扩展检索（LLM 生成查询变体，RRF 融合）
- `self_query`: 自查询检索（LLM 解析元数据过滤条件）
- `parent_document`: 父文档检索（小块检索返回父块上下文）
- `ensemble`: 集成检索（任意组合多检索器）
- `llama_dense`: LlamaIndex 稠密检索（真实 Embedding）
- `llama_bm25`: LlamaIndex BM25 检索（从 DB 加载）
- `llama_hybrid`: LlamaIndex 混合检索

### 查询增强 (Query Transforms)
- `HyDEQueryTransform`: 假设文档嵌入查询变换
- `QueryRouter`: 查询路由，自动选择检索策略
- `RAGFusionTransform`: 多查询扩展

### 文档增强 (Enrichers)
- `DocumentSummarizer`: 文档摘要生成
- `ChunkEnricher`: Chunk 上下文增强（默认关闭）

### 后处理 (Postprocessors)
- `ContextWindowExpander`: 上下文窗口扩展

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
- 向量库按租户隔离（每租户一个 Collection）
- 查询时强制过滤 `tenant_id`
- 租户可被禁用，禁用后所有 API Key 失效

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
