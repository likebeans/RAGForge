# Self-RAG Pipeline

多租户知识库检索服务，提供 OpenAI 兼容的 API 接口。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
- **🗂️ 知识库管理** - 创建、配置、删除知识库
- **📄 文档摄取** - 上传文档，自动切分、向量化、索引
- **🔍 语义检索** - 支持稠密向量、BM25、混合检索
- **🔑 API Key 认证** - 多租户隔离，请求限流

### 技术亮点
- **可插拔算法框架** - 切分器、检索器、查询变换可配置替换
- **多向量存储后端** - 支持 Qdrant（默认）、Milvus、Elasticsearch
- **LlamaIndex 集成** - 可选使用 LlamaIndex 的切分和检索能力
- **异步架构** - 基于 FastAPI + asyncpg，高并发性能
- **高级 RAG 功能** - HyDE、RAG Fusion、上下文窗口、文档摘要、查询路由

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
│    │PostgreSQL│  │  Qdrant  │  │  Milvus  │  │    ES    │      │
│    │(Metadata)│  │ (Vector) │  │ (Vector) │  │ (Vector) │      │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI |
| 数据库 ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 15 |
| 向量存储 | Qdrant / Milvus / Elasticsearch |
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
```

### 方式二：本地开发

```bash
# 1. 安装依赖
uv sync

# 2. 启动基础设施（PostgreSQL + Qdrant）
docker compose up -d db qdrant

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 4. 执行数据库迁移
uv run alembic upgrade head

# 5. 启动开发服务器
uv run uvicorn app.main:app --reload --port 8020
```

### 生成 API Key

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
| `GET` | `/health` | 健康检查 |
| **API Key 管理** |
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
| `POST` | `/v1/documents` | 上传文档 |
| `GET` | `/v1/documents` | 列出文档 |
| `DELETE` | `/v1/documents/{id}` | 删除文档 |
| **检索** |
| `POST` | `/v1/retrieve` | 执行检索（返回模型信息） |

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
      "hyde_queries": ["LLM生成的假设文档..."]  // HyDE 检索器返回
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",      // 使用 LLM 的检索器返回
    "llm_model": "qwen3:14b",
    "rerank_provider": null,
    "rerank_model": null,
    "retriever": "hyde"
  }
}
```

---

## 配置说明

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
| `DATABASE_URL` | `postgresql+asyncpg://kb:kb@localhost:5432/kb` | PostgreSQL 连接字符串 |
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
| **Qdrant** |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant 服务地址 |
| `QDRANT_API_KEY` | - | Qdrant API Key（云服务） |
| `QDRANT_COLLECTION_PREFIX` | `kb_` | Collection 前缀 |
| **Milvus（可选）** |
| `MILVUS_HOST` | - | Milvus 主机 |
| `MILVUS_PORT` | - | Milvus 端口 |
| **Elasticsearch（可选）** |
| `ES_HOSTS` | - | ES 主机（逗号分隔） |
| `ES_INDEX_PREFIX` | `kb_` | 索引前缀 |

### 端口配置

| 服务 | 容器端口 | 宿主机端口 |
|------|----------|------------|
| API | 8020 | 8020 |
| PostgreSQL | 5432 | 5435 |
| Qdrant | 6333 | 6333 |

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
│   ├── services/            # 业务逻辑层
│   │   ├── ingestion.py     # 文档摄取
│   │   └── query.py         # 检索服务
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
