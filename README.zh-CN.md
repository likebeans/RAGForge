# Self-RAG Pipeline

多租户知识库检索服务，提供 OpenAI 兼容的 API 接口和完整的 Python SDK。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | [文档](docs/) | [API 参考](docs/architecture/api-specification.md)

## 目录

- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [配置说明](#配置说明)
- [算法框架](#算法框架)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [部署指南](#部署指南)

---

## 功能特性

### 核心功能
- **👥 租户管理** - 创建、禁用、配额控制（Admin API）
- **🗂️ 知识库管理** - 创建、配置、删除知识库
- **📄 文档摄取** - 上传文档，自动切分、向量化、索引
- **🔍 语义检索** - 支持稠密向量、BM25、混合检索、Rerank
- **🤖 RAG 生成** - 多 LLM 提供商支持，检索增强生成
- **🔑 企业权限系统** - 三层权限模型（操作权限 + KB范围 + 文档ACL）
- **🔒 Security Trimming** - 检索时自动过滤无权限文档
- **🏢 多租户存储隔离** - Partition/Collection/Auto 三种策略
- **📊 可观测性** - 结构化日志、请求追踪、指标收集
- **📝 审计日志** - 全链路 API 访问记录，支持查询统计
- **🛠️ 运维接口** - 健康检查、就绪检查、系统指标
- **🔌 OpenAI 兼容接口** - Embeddings、Chat Completions（RAG 模式）
- **📦 Python SDK** - 完整的客户端库，支持所有功能

### 技术亮点
- **可插拔算法框架** - 切分器、检索器、查询变换可配置替换
- **多向量存储后端** - 支持 Qdrant（默认）、Milvus、Elasticsearch
- **LlamaIndex 集成** - 可选使用 LlamaIndex 的切分和检索能力
- **异步架构** - 基于 FastAPI + asyncpg，高并发性能
- **高级 RAG 功能**:
  - **HyDE** - LLM 生成假设文档，提升语义检索效果
  - **Multi-Query** - LLM 生成查询变体，RRF 融合
  - **RAPTOR** - 递归聚类 + LLM 摘要构建多层次索引树
  - **Parent-Child Chunking** - 父子分块，大块上下文 + 小块精确匹配
  - **Rerank** - 支持多种重排模型（bge-reranker、Cohere 等）
  - **文档摘要** - 摄取时自动生成文档摘要
  - **Chunk Enrichment** - LLM 增强 Chunk 上下文语义
  - **上下文窗口** - 检索结果自动扩展前后文

---

## 权限过滤流程（重要）

- 检索会先完成向量/BM25 等搜索，再做 ACL Security Trimming；不会提前拒绝。
- ACL 过滤依据 API Key 的 identity（user/roles/groups/clearance）与文档的 `sensitivity_level`/ACL 白名单。
- 命中结果但被 ACL 全部过滤时，接口返回 `403`，`code=NO_PERMISSION`（检索日志仍会记录命中数量）。
- 解决办法：使用具备更高 clearance 的 Key、调整文档 `sensitivity_level` 为 `public`，或在文档 ACL 白名单中加入该 Key 的用户/角色/用户组并重新索引。

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                    FastAPI (Port 8020)                          │
├─────────────────────────────────────────────────────────────────┤
│                        Service Layer                             │
│              ┌──────────────┐  ┌──────────────┐                 │
│              │  Ingestion   │  │    Query     │                 │
│              │   Service    │  │   Service    │                 │
│              └──────────────┘  └──────────────┘                 │
├─────────────────────────────────────────────────────────────────┤
│                      Pipeline Layer                              │
│         ┌────────────┐              ┌────────────┐              │
│         │  Chunkers  │              │ Retrievers │              │
│         ├────────────┤              ├────────────┤              │
│         │ • simple   │              │ • dense    │              │
│         │ • sliding  │              │ • bm25     │              │
│         │ • parent   │              │ • hybrid   │              │
│         │ • llama_*  │              │ • llama_*  │              │
│         └────────────┘              └────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                          │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│    │PostgreSQL│  │  Redis   │  │OpenSearch│  │  Milvus  │      │
│    │ 元数据   │  │ 缓存 &   │  │   BM25   │  │ (向量)   │      │
│    │ + 向量   │  │ 限流     │  │(可选)    │  │(可选)    │      │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI |
| 数据库 ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 15 (元数据 + pgvector) |
| 向量存储 | PostgreSQL pgvector (默认) / Milvus / Elasticsearch (可选) |
| 缓存 & 限流 | Redis 7 |
| BM25 存储 | 内存 (默认) / OpenSearch (生产环境) |
| 依赖管理 | uv |
| 数据库迁移 | Alembic |
| 容器化 | Docker + Docker Compose |

---

## 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- uv（推荐）或 pip

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone <repo-url>
cd self_rag_pipeline

# 2. 配置环境变量
cp .env.example .env

# 3. 启动所有服务
docker compose up -d

# 4. 执行数据库迁移
docker compose exec api uv run alembic upgrade head

# 5. 检查服务状态
curl http://localhost:8020/health
# 前端控制台
# 浏览器访问 http://localhost:3003
```

### 方式二：本地开发

```bash
# 1. 安装依赖
uv sync

# 2. 启动基础设施（PostgreSQL + Redis）
docker compose up -d db redis

# 3. 配置环境变量
cp .env.example .env.local
# 编辑 .env.local:
# - DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb
# - REDIS_URL=redis://localhost:6389/0
# - 填入真实的 API 密钥

# 4. 执行数据库迁移
uv run alembic upgrade head

# 5. 启动开发服务器
uv run uvicorn app.main:app --reload --port 8020
```

### 生成 API Key

**方式一：使用 Admin API（推荐）**

```bash
# 1. 确保设置了 ADMIN_TOKEN 环境变量（在 docker-compose.yml 或 .env 中）
export ADMIN_TOKEN="your-secure-admin-token"

# 2. 创建租户（自动返回初始 admin API Key）
curl -X POST "http://localhost:8020/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-tenant"}'

# 响应示例:
# {
#   "id": "xxx-xxx-xxx",
#   "name": "demo-tenant",
#   "status": "active",
#   "initial_api_key": "kb_sk_xxxxx..."  # 保存此 Key！
# }
```

**方式二：脚本生成（兼容旧方式）**

```bash
# 在容器内执行
cat <<'PY' | docker compose exec -T api uv run python -
import asyncio
from app.db.session import async_session_maker, init_models
from app.models import Tenant, APIKey
from app.auth.api_key import generate_api_key
from app.config import get_settings

async def main():
    await init_models()
    async with async_session_maker() as s:
        tenant = Tenant(name="demo-tenant")
        s.add(tenant)
        await s.flush()
        
        display, hashed, prefix = generate_api_key(get_settings().api_key_prefix)
        s.add(APIKey(
            tenant_id=tenant.id,
            name="default",
            prefix=prefix,
            hashed_key=hashed,
            role="admin",
            is_initial=True,
            revoked=False
        ))
        await s.commit()
        print("API_KEY:", display)

asyncio.run(main())
PY
```

### 验证安装

```bash
# 设置环境变量
export API_KEY="上面生成的 Key"
export API_BASE="http://localhost:8020"

# 创建知识库
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-kb", "description": "测试知识库"}'

# 运行端到端测试
uv run pytest test/test_live_e2e.py -v
```

---

## API 文档

启动服务后访问：
- **Swagger UI**: http://localhost:8020/docs
- **ReDoc**: http://localhost:8020/redoc

### API 端点一览

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health` | 存活检查（Liveness） |
| `GET` | `/ready` | 就绪检查（Readiness，检查 DB/Qdrant） |
| `GET` | `/metrics` | 系统指标（运行时间、调用统计） |
| **管理员接口** (需要 `X-Admin-Token` 头) |
| `POST` | `/admin/tenants` | 创建租户（返回初始 API Key） |
| `GET` | `/admin/tenants` | 列出租户 |
| `GET` | `/admin/tenants/{id}` | 租户详情 |
| `PATCH` | `/admin/tenants/{id}` | 更新租户 |
| `POST` | `/admin/tenants/{id}/disable` | 禁用租户 |
| `POST` | `/admin/tenants/{id}/enable` | 启用租户 |
| `DELETE` | `/admin/tenants/{id}` | 删除租户 |
| `GET` | `/admin/tenants/{id}/api-keys` | 列出租户 API Keys |
| `POST` | `/admin/tenants/{id}/api-keys` | 创建 API Key |
| **API Key 管理** (租户自管理) |
| `POST` | `/v1/api-keys` | 创建 API Key |
| `GET` | `/v1/api-keys` | 列出 API Keys |
| `DELETE` | `/v1/api-keys/{id}` | 删除 API Key |
| **知识库管理** |
| `POST` | `/v1/knowledge-bases` | 创建知识库 |
| `GET` | `/v1/knowledge-bases` | 列出知识库 |
| `GET` | `/v1/knowledge-bases/{id}` | 获取知识库详情 |
| `PATCH` | `/v1/knowledge-bases/{id}` | 更新知识库配置 |
| `DELETE` | `/v1/knowledge-bases/{id}` | 删除知识库 |
| **文档管理** |
| `POST` | `/v1/knowledge-bases/{kb_id}/documents` | 上传文档 |
| `GET` | `/v1/knowledge-bases/{kb_id}/documents` | 列出文档 |
| `DELETE` | `/v1/documents/{id}` | 删除文档 |
| **检索** |
| `POST` | `/v1/retrieve` | 执行检索（返回模型信息） |
| **RAG 生成** |
| `POST` | `/v1/rag` | RAG 生成（检索 + LLM 生成） |
| **OpenAI 兼容接口** |
| `POST` | `/v1/embeddings` | OpenAI Embeddings API |
| `POST` | `/v1/chat/completions` | OpenAI Chat Completions API（RAG 模式） |

### 请求示例

#### 创建知识库
```bash
curl -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tech-docs",
    "description": "技术文档知识库",
    "config": {
      "chunker": "sliding_window",
      "chunker_params": {"window": 512, "overlap": 50},
      "retriever": "hybrid",
      "retriever_params": {"dense_weight": 0.7, "sparse_weight": 0.3}
    }
  }'
```

#### 上传文档
```bash
curl -X POST "http://localhost:8020/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": "<kb_id>",
    "title": "API 设计指南",
    "content": "这是一份详细的 API 设计指南文档内容..."
  }'
```

#### 执行检索
```bash
curl -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_ids": ["<kb_id>"],
    "query": "如何设计 RESTful API？",
    "top_k": 5
  }'
```

#### 检索响应示例
```json
{
  "results": [
    {
      "chunk_id": "xxx",
      "text": "检索到的文本...",
      "score": 0.85,
      "metadata": {...},
      "knowledge_base_id": "kb_id",
      "hyde_queries": ["LLM生成的假设文档..."],      // HyDE 检索器返回
      "generated_queries": ["查询变体1", "查询变体2"],  // multi_query 检索器返回
      "retrieval_details": [...]                     // multi_query 每个查询的完整检索结果
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",      // 使用 LLM 的检索器返回（hyde/multi_query）
    "llm_model": "qwen3:14b",
    "rerank_provider": null,       // fusion + rerank 时返回
    "rerank_model": null,
    "retriever": "hyde"            // 使用的检索器名称
  }
}
```

#### RAG 生成
```bash
curl -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 有什么特点？",
    "knowledge_base_ids": ["<kb_id>"],
    "top_k": 5,
    "temperature": 0.7
  }'
```

#### RAG 响应示例
```json
{
  "answer": "Python 是一种解释型、面向对象的高级编程语言...",
  "sources": [
    {
      "chunk_id": "xxx",
      "text": "检索到的文本...",
      "score": 0.85,
      "document_id": "doc_xxx",
      "knowledge_base_id": "kb_xxx"
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "retriever": "dense"
  }
}
```

---

## 配置说明

### 环境文件结构

```
.env.example  → 配置模板（包含所有选项和详细说明） ✅ 提交到 Git
.env          → Docker 环境默认配置（容器间通信）    🔒 Git 忽略
.env.local    → 本地开发覆盖配置（真实 API 密钥）   🔒 Git 忽略
```

**配置优先级**：环境变量 > `.env.local` > `.env` > 默认值

### Docker Compose 配置

#### 主配置 (`docker-compose.yml`)

**技术栈**：PostgreSQL + Redis + API + Frontend

**BM25 存储**：内存索引（从 PostgreSQL 启动时加载）
- ✅ 开发和小规模使用快速
- ✅ 数据持久化在 PostgreSQL
- ⚠️ 重启时需要重建索引
- ⚠️ 不推荐多副本部署

```bash
# 启动服务
docker compose up -d

# 访问
# - API: http://localhost:8020
# - 前端: http://localhost:3003
# - PostgreSQL: localhost:5435
# - Redis: localhost:6389
```

#### OpenSearch 配置 (`docker-compose.opensearch.yml`)

**技术栈**：PostgreSQL + Redis + OpenSearch + API + Frontend

**BM25 存储**：OpenSearch 持久化索引
- ✅ 生产级持久化存储
- ✅ 多副本安全（共享索引）
- ✅ 适合大规模数据
- ℹ️ 需要额外资源

```bash
# 启动服务
docker compose -f docker-compose.opensearch.yml up -d

# 访问
# - API: http://localhost:8021
# - 前端: http://localhost:3004
# - PostgreSQL: localhost:5436
# - Redis: localhost:6390
# - OpenSearch: http://localhost:9200
```

### BM25 存储架构对比

| 配置 | 数据存储 | BM25 索引 | 重启后 | 多副本 | 使用场景 |
|------|---------|----------|--------|--------|---------|
| **主配置** | PostgreSQL | 内存 | 从 DB 重建 | ❌ 不一致 | 开发、小规模 |
| **OpenSearch 配置** | PostgreSQL | OpenSearch | 保留 | ✅ 一致 | 生产、大规模 |

**两种配置都**：
- 使用 PostgreSQL 存储 chunks 持久化数据
- 使用 PostgreSQL + pgvector 存储向量
- 使用 Redis 进行缓存和限流

### 端口映射

| 服务 | 主配置 | OpenSearch 配置 |
|------|--------|----------------|
| API | 8020 | 8021 |
| 前端 | 3003 | 3004 |
| PostgreSQL | 5435 | 5436 |
| Redis | 6389 | 6390 |
| OpenSearch | - | 9200 |

### 模型提供商

支持多种 LLM/Embedding/Rerank 提供商：

| 提供商 | LLM | Embedding | Rerank | 说明 |
|--------|-----|-----------|--------|------|
| **Ollama** | ✅ | ✅ | ✅ | 本地部署，免费（推荐开发） |
| **OpenAI** | ✅ | ✅ | - | GPT-4, text-embedding-3 |
| **Gemini** | ✅ | ✅ | - | Google AI |
| **Qwen** | ✅ | ✅ | - | 阿里云 DashScope |
| **Kimi** | ✅ | - | - | 月之暗面 Moonshot |
| **DeepSeek** | ✅ | ✅ | - | DeepSeek |
| **智谱 AI** | ✅ | ✅ | ✅ | GLM 系列 |
| **SiliconFlow** | ✅ | ✅ | ✅ | 聚合多种开源模型 |
| **Cohere** | - | - | ✅ | 专业 Rerank 服务 |

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| **应用配置** |
| `ENVIRONMENT` | `dev` | 运行环境：dev/staging/prod |
| **数据库** |
| `DATABASE_URL` | `postgresql+asyncpg://kb:kb@localhost:5435/kb` | PostgreSQL 连接字符串 |
| **向量存储** |
| `VECTOR_STORE` | `postgresql` | 向量存储类型（使用 pgvector） |
| **Redis 配置** |
| `REDIS_URL` | `redis://localhost:6389/0` | Redis 连接字符串 |
| `REDIS_CACHE_ENABLED` | `true` | 是否启用查询缓存 |
| `REDIS_CACHE_TTL` | `300` | 查询缓存过期时间（秒） |
| `REDIS_CONFIG_CACHE_TTL` | `600` | 配置缓存过期时间（秒） |
| **认证** |
| `API_KEY_PREFIX` | `kb_sk_` | API Key 前缀 |
| `API_RATE_LIMIT_PER_MINUTE` | `120` | 每分钟请求限制 |
| **模型提供商 API Keys** |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `GEMINI_API_KEY` | - | Google Gemini API Key |
| `QWEN_API_KEY` | - | 阿里云 DashScope API Key |
| `KIMI_API_KEY` | - | 月之暗面 Moonshot API Key |
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key |
| `ZHIPU_API_KEY` | - | 智谱 AI API Key |
| `SILICONFLOW_API_KEY` | - | SiliconFlow API Key |
| `COHERE_API_KEY` | - | Cohere API Key (Rerank) |
| **LLM 配置** |
| `LLM_PROVIDER` | `ollama` | LLM 提供商 |
| `LLM_MODEL` | `qwen3:14b` | LLM 模型名称 |
| `LLM_TEMPERATURE` | `0.7` | 温度参数 |
| `LLM_MAX_TOKENS` | `2048` | 最大生成 token |
| **Embedding 配置** |
| `EMBEDDING_PROVIDER` | `ollama` | Embedding 提供商 |
| `EMBEDDING_MODEL` | `bge-m3` | Embedding 模型名称 |
| `EMBEDDING_DIM` | `1024` | 向量维度 |
| **Rerank 配置** |
| `RERANK_PROVIDER` | `none` | Rerank 提供商（none 禁用） |
| `RERANK_MODEL` | - | Rerank 模型名称 |
| `RERANK_TOP_K` | `10` | 重排返回数量 |
| **Rerank 请求覆盖说明** | - | 前端/接口传入的 `rerank_override` 只需指定 `provider`、`model`；若未传 `api_key`/`base_url`，会自动回落到环境/系统配置（如 `SILICONFLOW_API_KEY`、`COHERE_API_KEY` 等） |
| **BM25/稀疏检索** |
| `BM25_ENABLED` | `true` | 是否启用稀疏检索 |
| `BM25_BACKEND` | `memory` | `memory`（内存）/ `es`（OpenSearch/ES） |
| **Milvus（可选）** |
| `MILVUS_HOST` | - | Milvus 主机 |
| `MILVUS_PORT` | - | Milvus 端口 |
| **Elasticsearch（可选）** |
| `ES_HOSTS` | - | ES 主机（逗号分隔） |
| `ES_USERNAME` / `ES_PASSWORD` | - | 认证信息（可选） |
| `ES_INDEX_PREFIX` | `kb_` | 索引前缀 |
| `ES_INDEX_MODE` | `shared` | `shared` 单索引或 `per_kb` 每 KB 一索引 |
| `ES_REQUEST_TIMEOUT` | `10` | 请求超时时间（秒） |
| `ES_BULK_BATCH_SIZE` | `500` | bulk 写入批大小 |
| `ES_ANALYZER` | `standard` | 索引 analyzer，中文可换 IK 等 |
| `ES_REFRESH` | `false` | bulk 写入刷新策略 |

> 稀疏检索运维脚本：
> - `scripts/migrate_bm25_to_es.py`：DB → ES/OpenSearch 迁移/双写。
> - `scripts/manage_es_indices.py`：列出/删除/刷新索引。
> - `scripts/rebuild_bm25.py`：从 DB 重建内存 BM25（回滚时用）。
> 更多迁移细节见 `docs/MIGRATION_SPARSE_ES.md`。

> Qdrant 多向量字段：同一 Collection 支持多模型/多维度的向量字段，字段名自动由模型+维度生成（如 `vec_qwen_embedding_4096`）。保持入库与检索的模型一致即可避免维度错误。

### 旧版配置说明（已废弃）

> ⚠️ **注意**：以下配置项已废弃，仅保留用于参考
> 
> - ~~`QDRANT_URL`~~ - 已移除，现使用 PostgreSQL + pgvector
> - ~~`QDRANT_API_KEY`~~ - 已移除
> - ~~`QDRANT_COLLECTION_PREFIX`~~ - 已移除

---

## 权限系统

### 三层权限模型

```
┌─────────────────────────────────────────────────────────────┐
│ 第一层：操作权限 (APIKey.role)                               │
│   admin → 全部权限 + 管理 API Key                           │
│   write → 创建 KB、上传文档、检索                            │
│   read  → 仅检索和列表                                      │
├─────────────────────────────────────────────────────────────┤
│ 第二层：KB 范围 (APIKey.scope_kb_ids)                       │
│   白名单模式，null 表示不限制                                │
├─────────────────────────────────────────────────────────────┤
│ 第三层：文档过滤 (sensitivity + ACL)                         │
│   public     → 租户内所有 Key 可访问                         │
│   restricted → 需要 ACL 白名单匹配                           │
└─────────────────────────────────────────────────────────────┘
```

### 创建带身份的 API Key

```bash
curl -X POST "http://localhost:8020/admin/tenants/{id}/api-keys" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "销售部专用 Key",
    "role": "read",
    "scope_kb_ids": ["kb_sales", "kb_products"],
    "identity": {
      "user_id": "sales_team",
      "roles": ["sales", "viewer"],
      "groups": ["dept_sales"],
      "clearance": "restricted"
    }
  }'
```

### 文档敏感度设置

```bash
# 上传受限文档（需要 ACL 匹配）
curl -X POST "http://localhost:8020/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": "<kb_id>",
    "title": "销售策略文档",
    "content": "机密内容...",
    "sensitivity_level": "restricted",
    "acl_allow_roles": ["sales", "manager"],
    "acl_allow_groups": ["dept_sales"]
  }'
```

---

## 算法框架

### 切分器 (Chunkers)

| 名称 | 说明 | 适用场景 |
|------|------|----------|
| `simple` | 按段落切分（双换行符） | 简单场景 |
| `sliding_window` | 滑动窗口切分，支持重叠 | 通用文档 |
| `recursive` | 递归字符切分 | 通用文档（推荐） |
| `markdown` | Markdown 感知切分 | 技术文档 |
| `code` | 代码感知切分（按语法结构） | 代码库 |
| `parent_child` | 父子分块，大块索引+小块检索 | 长篇文章 |
| `llama_sentence` | LlamaIndex 句子级切分 | 精确问答 |
| `llama_token` | LlamaIndex Token 级切分 | Token 敏感场景 |

### 检索器 (Retrievers)

| 名称 | 说明 | 适用场景 |
|------|------|----------|
| `dense` | 稠密向量检索 | 语义相似 |
| `bm25` | BM25 稀疏检索（从 DB 加载，支持持久化） | 精确匹配 |
| `hybrid` | Dense + BM25 混合检索 | 通用问答（推荐） |
| `fusion` | 融合检索（RRF + Rerank） | 高质量召回 |
| `hyde` | HyDE 检索器（LLM 生成假设文档） | 复杂语义问题 |
| `multi_query` | 多查询扩展检索（LLM 生成查询变体） | 提高召回率 |
| `self_query` | 自查询检索（LLM 解析元数据过滤） | 结构化过滤 |
| `parent_document` | 父文档检索（小块检索返回父块） | 长文档上下文 |
| `ensemble` | 集成检索（任意组合多检索器） | 灵活多路召回 |
| `llama_dense` | LlamaIndex 稠密检索（真实 Embedding） | 多后端切换 |
| `llama_bm25` | LlamaIndex BM25 检索 | 大规模数据（带缓存） |
| `llama_hybrid` | LlamaIndex 混合检索 | 多后端 + 混合 |

### 高级功能

| 功能 | 说明 |
|------|------|
| **查询路由** | 根据查询类型自动选择检索策略 |
| **RAG Fusion** | 多查询扩展，提高召回覆盖率 |
| **HyDE** | 假设文档嵌入，提升语义匹配 |
| **上下文窗口** | 检索后扩展前后 chunk 上下文 |
| **文档摘要** | 自动生成文档摘要 |
| **Chunk Enrichment** | LLM 增强 chunk 语义（可选） |

### 知识库配置示例

```json
{
  "config": {
    "chunker": "sliding_window",
    "chunker_params": {
      "window": 1024,
      "overlap": 100
    },
    "retriever": "hybrid",
    "retriever_params": {
      "dense_weight": 0.7,
      "sparse_weight": 0.3
    },
    "store_type": "qdrant"
  }
}
```

更多配置示例参见 `docs/phase2.md`。

---

## 项目结构

```
self_rag_pipeline/
├── app/                      # 应用代码
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由层
│   │   ├── deps.py          # 依赖注入
│   │   └── routes/          # 各功能路由
│   ├── auth/                # 认证模块
│   │   └── api_key.py       # API Key 认证
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic 数据模型
│   │   └── internal.py      # 服务层内部参数模型
│   ├── services/            # 业务逻辑层
│   │   ├── ingestion.py     # 文档摄取
│   │   ├── query.py         # 检索服务
│   │   └── rag.py           # RAG 生成服务
│   ├── pipeline/            # 算法框架
│   │   ├── base.py          # 基础协议
│   │   ├── registry.py      # 算法注册表
│   │   ├── chunkers/        # 切分器（simple/sliding/recursive/markdown/code 等）
│   │   ├── retrievers/      # 检索器（dense/bm25/hybrid/fusion/hyde 等）
│   │   ├── query_transforms/ # 查询变换（HyDE/Router/RAGFusion）
│   │   ├── enrichers/       # 文档增强（Summary/ChunkEnricher）
│   │   └── postprocessors/  # 后处理（ContextWindow）
│   ├── infra/               # 基础设施
│   │   ├── llm.py           # LLM 客户端（多提供商）
│   │   ├── embeddings.py    # 向量化（多提供商）
│   │   ├── rerank.py        # 重排模块（多提供商）
│   │   ├── vector_store.py  # Qdrant 操作
│   │   ├── bm25_store.py    # BM25 存储
│   │   └── llamaindex.py    # LlamaIndex 集成
│   └── db/                  # 数据库配置
├── alembic/                 # 数据库迁移
├── sdk/                     # Python SDK
├── tests/                   # 测试文件
├── docs/                    # 项目文档
├── docker-compose.yml       # Docker 编排
├── Dockerfile               # 镜像构建
├── pyproject.toml           # 项目配置
└── AGENTS.md                # AI 助手指南
```

---

## 开发指南

### 运行测试

```bash
# 单元测试
uv run pytest tests/ -v

# 端到端测试（需要启动服务）
API_KEY="your_key" API_BASE="http://localhost:8020" uv run pytest test/test_live_e2e.py -v

# 类型检查
uv run mypy app/

# 代码格式化
uv run ruff format .
uv run ruff check --fix .
```

### 数据库迁移

```bash
# 创建迁移
uv run alembic revision --autogenerate -m "描述"

# 执行迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1
```

### 添加新功能

1. **添加新切分器**: 参见 `app/pipeline/chunkers/AGENTS.md`
2. **添加新检索器**: 参见 `app/pipeline/retrievers/AGENTS.md`
3. **添加新 API**: 参见 `app/api/AGENTS.md`
4. **添加新模型**: 参见 `app/models/AGENTS.md`

---

## 部署指南

### Docker 部署

```bash
# 构建镜像（使用宿主机网络加速）
docker build --network=host -t self_rag_pipeline-api .

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f api
```

### 生产环境建议

1. **安全**
   - 启用 HTTPS（使用 Nginx 反向代理）
   - 定期轮换 API Key
   - 配置防火墙规则

2. **性能**
   - 调整 `API_RATE_LIMIT_PER_MINUTE` 限流配置
   - 使用 Redis 替换内存限流器
   - 配置连接池大小

3. **高可用**
   - PostgreSQL 主从复制
   - Qdrant 集群模式
   - 多实例部署 + 负载均衡

4. **监控**
   - 接入 Prometheus + Grafana
   - 配置日志收集（ELK）
   - 设置告警规则

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！

开发前请阅读：
- `AGENTS.md` - 项目概述和开发指南
- `app/*/AGENTS.md` - 各模块详细文档

---

**For English documentation, see [README.md](README.md)**
