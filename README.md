# RAGForge

<p align="center">
  <strong>Multi-tenant Knowledge Base Retrieval Service with OpenAI-compatible API</strong>
</p>

<p align="center">
  Enterprise-grade multi-tenant knowledge base retrieval service with OpenAI-compatible API and complete Python SDK.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="./docs/"><img src="https://img.shields.io/badge/docs-VitePress-646cff.svg" alt="Documentation"></a>
</p>

<p align="center">
  English | <a href="README.zh-CN.md">中文</a> | <a href="./docs/">Docs</a> | <a href="./docs/architecture/api-specification.md">API Reference</a>
</p>

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Permission System](#permission-system)
- [Security Features](#security-features)
- [Pipeline Framework](#pipeline-framework)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Documentation](#documentation)

> 📚 **Full Documentation**: Visit [docs/](./docs/) for the VitePress documentation site with detailed guides, architecture design, and development docs.

---

## Features

### Core Features
- **🏢 Multi-tenant Architecture** - Complete tenant isolation, quota management, and permission control
- **🔌 OpenAI-compatible API** - Embeddings, Chat Completions API for seamless integration
- **🧠 Advanced Retrieval Algorithms** - Dense/BM25/Hybrid/RAPTOR and more
- **🔄 Pluggable Architecture** - Modular design with custom chunkers, retrievers, and enrichers
- **🌐 Multi-LLM Providers** - OpenAI, Ollama, Qwen, Zhipu AI, and more
- **📊 Full Observability** - Structured logging, request tracing, audit logs, and metrics
- **🐍 Python SDK** - Complete client library supporting all features
- **🚀 Production Ready** - Docker deployment, database migrations, configuration management

### Security Features
- **🔑 Three-layer Permission Model** - Operation permissions + KB scope + Document ACL
- **🔒 Security Trimming** - Automatic filtering of unauthorized documents during retrieval
- **🔐 Credential Manager** - Primary/fallback keys, auto-failover, key rotation
- **🛡️ Credential Scanner** - Pre-commit hooks to detect hardcoded secrets
- **📝 Audit Logs** - Full API access logging with query statistics

### Technical Highlights
- **Pluggable Algorithm Framework** - Configurable chunkers, retrievers, query transforms
- **Multiple Vector Store Backends** - Qdrant (default), Milvus, Elasticsearch
- **LlamaIndex Integration** - Optional LlamaIndex chunking and retrieval
- **Async Architecture** - FastAPI + asyncpg for high concurrency
- **Advanced RAG Features**:
  - **HyDE** - LLM-generated hypothetical documents for better semantic retrieval
  - **Multi-Query** - LLM-generated query variants with RRF fusion
  - **RAPTOR** - Recursive clustering + LLM summarization for hierarchical indexing
  - **Parent-Child Chunking** - Large context + small precise matching
  - **Rerank** - Multiple reranking models (bge-reranker, Cohere, etc.)
  - **Document Summarization** - Auto-generate summaries during ingestion
  - **Chunk Enrichment** - LLM-enhanced chunk context semantics
  - **Context Window** - Auto-expand surrounding context in results

---

## Permission Filtering Process (Important)

- Retrieval completes vector/BM25 search first, then applies ACL Security Trimming; requests are not rejected early.
- ACL filtering uses API Key identity (user/roles/groups/clearance) against document `sensitivity_level` and ACL whitelist.
- When all results are filtered by ACL, the API returns `403` with `code=NO_PERMISSION` (retrieval logs still record hit counts).
- Solutions: Use a Key with higher clearance, set document `sensitivity_level` to `public`, or add the Key's user/roles/groups to the document ACL whitelist and re-index.

---

## Architecture

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

### Tech Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI |
| Database ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 |
| Vector Store | Qdrant / Milvus / Elasticsearch |
| Package Manager | uv |
| DB Migrations | Alembic |
| Containerization | Docker + Docker Compose |

---

## Quick Start

### Requirements

- Python 3.11+
- Docker & Docker Compose
- uv (recommended) or pip

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the project
git clone <repo-url>
cd RAGForge

# 2. Configure environment variables
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec api uv run alembic upgrade head

# 5. Check service status
curl http://localhost:8020/health
# Frontend console
# Visit http://localhost:3003 in browser
```

### Option 2: Local Development

```bash
# 1. Install dependencies
uv sync

# 2. Start infrastructure (PostgreSQL + Qdrant)
docker compose up -d db qdrant

# 3. Configure environment variables
cp .env.example .env
# Edit .env, set DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 4. Run database migrations
uv run alembic upgrade head

# 5. Start development server
uv run uvicorn app.main:app --reload --port 8020
```

### Local OpenSearch Sparse Retrieval (Optional)
```bash
# Start with OpenSearch (includes API + Postgres + OpenSearch)
docker compose -f docker-compose.opensearch.yml up -d

# Switch sparse retrieval to ES/OpenSearch
export BM25_ENABLED=true
export BM25_BACKEND=es
export ES_HOSTS=http://localhost:9200
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8020
```

### Generate API Key

**Option 1: Using Admin API (Recommended)**

```bash
# 1. Ensure ADMIN_TOKEN is set (in docker-compose.yml or .env)
export ADMIN_TOKEN="your-secure-admin-token"

# 2. Create tenant (returns initial admin API Key)
curl -X POST "http://localhost:8020/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-tenant"}'

# Response example:
# {
#   "id": "xxx-xxx-xxx",
#   "name": "demo-tenant",
#   "status": "active",
#   "initial_api_key": "kb_sk_xxxxx..."  # Save this Key!
# }
```

**Option 2: Script Generation (Legacy)**

```bash
# Execute inside container
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

### Verify Installation

```bash
# Set environment variables
export API_KEY="your-generated-key"
export API_BASE="http://localhost:8020"

# Create knowledge base
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-kb", "description": "Test knowledge base"}'

# Run end-to-end tests
uv run pytest test/test_live_e2e.py -v
```

---

## API Documentation

After starting the service, visit:
- **Swagger UI**: http://localhost:8020/docs
- **ReDoc**: http://localhost:8020/redoc

### API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness check (DB/Qdrant) |
| `GET` | `/metrics` | System metrics (uptime, call stats) |
| **Admin Endpoints** (requires `X-Admin-Token` header) |
| `POST` | `/admin/tenants` | Create tenant (returns initial API Key) |
| `GET` | `/admin/tenants` | List tenants |
| `GET` | `/admin/tenants/{id}` | Tenant details |
| `PATCH` | `/admin/tenants/{id}` | Update tenant |
| `POST` | `/admin/tenants/{id}/disable` | Disable tenant |
| `POST` | `/admin/tenants/{id}/enable` | Enable tenant |
| `DELETE` | `/admin/tenants/{id}` | Delete tenant |
| `GET` | `/admin/tenants/{id}/api-keys` | List tenant API Keys |
| `POST` | `/admin/tenants/{id}/api-keys` | Create API Key |
| **API Key Management** (tenant self-service) |
| `POST` | `/v1/api-keys` | Create API Key |
| `GET` | `/v1/api-keys` | List API Keys |
| `DELETE` | `/v1/api-keys/{id}` | Delete API Key |
| **Knowledge Base Management** |
| `POST` | `/v1/knowledge-bases` | Create knowledge base |
| `GET` | `/v1/knowledge-bases` | List knowledge bases |
| `GET` | `/v1/knowledge-bases/{id}` | Get knowledge base details |
| `PATCH` | `/v1/knowledge-bases/{id}` | Update knowledge base config |
| `DELETE` | `/v1/knowledge-bases/{id}` | Delete knowledge base |
| **Document Management** |
| `POST` | `/v1/knowledge-bases/{kb_id}/documents` | Upload document |
| `GET` | `/v1/knowledge-bases/{kb_id}/documents` | List documents |
| `DELETE` | `/v1/documents/{id}` | Delete document |
| **Retrieval** |
| `POST` | `/v1/retrieve` | Execute retrieval (returns model info) |
| **RAG Generation** |
| `POST` | `/v1/rag` | RAG generation (retrieval + LLM) |
| **OpenAI-compatible Endpoints** |
| `POST` | `/v1/embeddings` | OpenAI Embeddings API |
| `POST` | `/v1/chat/completions` | OpenAI Chat Completions API (RAG mode) |

### Request Examples

#### Create Knowledge Base
```bash
curl -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tech-docs",
    "description": "Technical documentation KB",
    "config": {
      "chunker": "sliding_window",
      "chunker_params": {"window": 512, "overlap": 50},
      "retriever": "hybrid",
      "retriever_params": {"dense_weight": 0.7, "sparse_weight": 0.3}
    }
  }'
```

#### Upload Document
```bash
curl -X POST "http://localhost:8020/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": "<kb_id>",
    "title": "API Design Guide",
    "content": "This is a detailed API design guide document..."
  }'
```

#### Execute Retrieval
```bash
curl -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_ids": ["<kb_id>"],
    "query": "How to design RESTful API?",
    "top_k": 5
  }'
```

#### Retrieval Response Example
```json
{
  "results": [
    {
      "chunk_id": "xxx",
      "text": "Retrieved text...",
      "score": 0.85,
      "metadata": {...},
      "knowledge_base_id": "kb_id",
      "hyde_queries": ["LLM-generated hypothetical doc..."],  // HyDE retriever returns
      "generated_queries": ["query variant 1", "query variant 2"],  // multi_query retriever returns
      "retrieval_details": [...]                     // multi_query full retrieval results
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",      // LLM-based retrievers return (hyde/multi_query)
    "llm_model": "qwen3:14b",
    "rerank_provider": null,       // fusion + rerank returns
    "rerank_model": null,
    "retriever": "hyde"            // retriever name used
  }
}
```

#### RAG Generation
```bash
curl -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are Python's features?",
    "knowledge_base_ids": ["<kb_id>"],
    "top_k": 5,
    "temperature": 0.7
  }'
```

#### RAG Response Example
```json
{
  "answer": "Python is an interpreted, object-oriented high-level programming language...",
  "sources": [
    {
      "chunk_id": "xxx",
      "text": "Retrieved text...",
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

## Configuration

### Model Providers

Supports multiple LLM/Embedding/Rerank providers:

| Provider | LLM | Embedding | Rerank | Notes |
|----------|-----|-----------|--------|-------|
| **Ollama** | ✅ | ✅ | ✅ | Local deployment, free (recommended for dev) |
| **OpenAI** | ✅ | ✅ | - | GPT-4, text-embedding-3 |
| **Gemini** | ✅ | ✅ | - | Google AI |
| **Qwen** | ✅ | ✅ | - | Alibaba DashScope |
| **Kimi** | ✅ | - | - | Moonshot AI |
| **DeepSeek** | ✅ | ✅ | - | DeepSeek |
| **Zhipu AI** | ✅ | ✅ | ✅ | GLM series |
| **SiliconFlow** | ✅ | ✅ | ✅ | Aggregates open-source models |
| **Cohere** | - | - | ✅ | Professional Rerank service |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| **Application** |
| `ENVIRONMENT` | `dev` | Runtime environment: dev/staging/prod |
| **Database** |
| `DATABASE_URL` | `postgresql+asyncpg://kb:kb@localhost:5432/kb` | PostgreSQL connection string |
| **Authentication** |
| `API_KEY_PREFIX` | `kb_sk_` | API Key prefix |
| `API_RATE_LIMIT_PER_MINUTE` | `120` | Request rate limit per minute |
| **Model Provider API Keys** |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `GEMINI_API_KEY` | - | Google Gemini API Key |
| `QWEN_API_KEY` | - | Alibaba DashScope API Key |
| `KIMI_API_KEY` | - | Moonshot API Key |
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key |
| `ZHIPU_API_KEY` | - | Zhipu AI API Key |
| `SILICONFLOW_API_KEY` | - | SiliconFlow API Key |
| `COHERE_API_KEY` | - | Cohere API Key (Rerank) |
| **LLM Configuration** |
| `LLM_PROVIDER` | `ollama` | LLM provider |
| `LLM_MODEL` | `qwen3:14b` | LLM model name |
| `LLM_TEMPERATURE` | `0.7` | Temperature parameter |
| `LLM_MAX_TOKENS` | `2048` | Max generation tokens |
| **Embedding Configuration** |
| `EMBEDDING_PROVIDER` | `ollama` | Embedding provider |
| `EMBEDDING_MODEL` | `bge-m3` | Embedding model name |
| `EMBEDDING_DIM` | `1024` | Vector dimension |
| **Rerank Configuration** |
| `RERANK_PROVIDER` | `none` | Rerank provider (none to disable) |
| `RERANK_MODEL` | - | Rerank model name |
| `RERANK_TOP_K` | `10` | Rerank return count |
| **Rerank Override** | - | Frontend/API `rerank_override` only needs `provider`, `model`; if `api_key`/`base_url` not provided, falls back to environment config |
| **Qdrant** |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant service URL |
| `QDRANT_API_KEY` | - | Qdrant API Key (cloud) |
| `QDRANT_COLLECTION_PREFIX` | `kb_` | Collection prefix |
| **BM25/Sparse Retrieval** |
| `BM25_ENABLED` | `true` | Enable sparse retrieval |
| `BM25_BACKEND` | `memory` | `memory` / `es` (OpenSearch/ES) |
| **Milvus (Optional)** |
| `MILVUS_HOST` | - | Milvus host |
| `MILVUS_PORT` | - | Milvus port |
| **Elasticsearch (Optional)** |
| `ES_HOSTS` | - | ES hosts (comma-separated) |
| `ES_USERNAME` / `ES_PASSWORD` | - | Auth credentials (optional) |
| `ES_INDEX_PREFIX` | `kb_` | Index prefix |
| `ES_INDEX_MODE` | `shared` | `shared` single index or `per_kb` per KB |
| `ES_REQUEST_TIMEOUT` | `10` | Request timeout (seconds) |
| `ES_BULK_BATCH_SIZE` | `500` | Bulk write batch size |
| `ES_ANALYZER` | `standard` | Index analyzer |
| `ES_REFRESH` | `false` | Bulk write refresh policy |

> Sparse retrieval scripts:
> - `scripts/migrate_bm25_to_es.py`: DB → ES/OpenSearch migration/dual-write.
> - `scripts/manage_es_indices.py`: List/delete/refresh indices.
> - `scripts/rebuild_bm25.py`: Rebuild in-memory BM25 from DB (for rollback).
> See `docs/MIGRATION_SPARSE_ES.md` for migration details.

> Qdrant multi-vector fields: Same Collection supports multiple model/dimension vector fields, field names auto-generated from model+dimension (e.g., `vec_qwen_embedding_4096`). Keep ingestion and retrieval models consistent to avoid dimension errors.

### Port Configuration

| Service | Container Port | Host Port |
|---------|----------------|-----------|
| API | 8020 | 8020 |
| PostgreSQL | 5432 | 5435 |
| Qdrant | 6333 | 6333 |

---

## Permission System

### Three-layer Permission Model

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Operation Permissions (APIKey.role)               │
│   admin → Full access + manage API Keys                    │
│   write → Create KB, upload docs, retrieve                 │
│   read  → Retrieve and list only                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: KB Scope (APIKey.scope_kb_ids)                     │
│   Whitelist mode, null means no restriction                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Document Filter (sensitivity + ACL)                │
│   public     → All Keys in tenant can access               │
│   restricted → Requires ACL whitelist match                │
└─────────────────────────────────────────────────────────────┘
```

### Create API Key with Identity

```bash
curl -X POST "http://localhost:8020/admin/tenants/{id}/api-keys" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Department Key",
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

### Document Sensitivity Settings

```bash
# Upload restricted document (requires ACL match)
curl -X POST "http://localhost:8020/v1/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": "<kb_id>",
    "title": "Sales Strategy Document",
    "content": "Confidential content...",
    "sensitivity_level": "restricted",
    "acl_allow_roles": ["sales", "manager"],
    "acl_allow_groups": ["dept_sales"]
  }'
```

---

## Security Features

### Credential Manager

Complete API key management capabilities:

- **Primary/Fallback Keys** - Each provider can have primary and fallback keys
- **Auto Failover** - Automatically switch to fallback when primary fails
- **Key Rotation** - Seamless key rotation, old primary auto-demotes to fallback
- **Key Validation** - Auto-validate key formats (OpenAI sk- prefix, Gemini AIzaSy prefix, etc.)
- **Expiry Detection** - Detect if keys need rotation based on last validation time

```python
from app.security.credential_manager import CredentialManager

manager = CredentialManager(settings)
api_key = manager.get_api_key("openai")  # Auto primary/fallback switch
await manager.rotate_key("openai", "new-key")  # Rotate key
```

### Credential Scanner

Automatically detect hardcoded credentials and sensitive information:

- **Detection Patterns** - API keys, generic passwords, weak tokens, internal IPs
- **Pre-commit Integration** - Auto-scan before commit to prevent key leakage
- **Whitelist Mechanism** - Support `.secrets.baseline` for known safe exceptions

```bash
# Install and enable pre-commit hooks
pip install pre-commit
pre-commit install

# Manual scan
python scripts/pre-commit-security-check.py --all
```

See [docs/SECURITY.md](./docs/SECURITY.md) for details.

---

## Pipeline Framework

### Chunkers

| Name | Description | Use Case |
|------|-------------|----------|
| `simple` | Split by paragraph (double newline) | Simple cases |
| `sliding_window` | Sliding window with overlap | General documents |
| `recursive` | Recursive character splitting | General documents (recommended) |
| `markdown` | Markdown-aware splitting | Technical docs |
| `code` | Code-aware splitting (by syntax) | Codebases |
| `parent_child` | Parent-child chunking | Long articles |
| `llama_sentence` | LlamaIndex sentence-level | Precise Q&A |
| `llama_token` | LlamaIndex token-level | Token-sensitive cases |

### Retrievers

| Name | Description | Use Case |
|------|-------------|----------|
| `dense` | Dense vector retrieval | Semantic similarity |
| `bm25` | BM25 sparse retrieval (DB-loaded, persistent) | Exact matching |
| `hybrid` | Dense + BM25 hybrid | General Q&A (recommended) |
| `fusion` | Fusion retrieval (RRF + Rerank) | High-quality recall |
| `hyde` | HyDE retriever (LLM hypothetical docs) | Complex semantic queries |
| `multi_query` | Multi-query expansion (LLM variants) | Improve recall |
| `self_query` | Self-query (LLM metadata parsing) | Structured filtering |
| `parent_document` | Parent document retrieval | Long document context |
| `ensemble` | Ensemble retrieval (combine multiple) | Flexible multi-path recall |
| `llama_dense` | LlamaIndex dense retrieval | Multi-backend switching |
| `llama_bm25` | LlamaIndex BM25 retrieval | Large-scale data (cached) |
| `llama_hybrid` | LlamaIndex hybrid retrieval | Multi-backend + hybrid |

### Advanced Features

| Feature | Description |
|---------|-------------|
| **Query Routing** | Auto-select retrieval strategy by query type |
| **RAG Fusion** | Multi-query expansion for better recall coverage |
| **HyDE** | Hypothetical document embedding for semantic matching |
| **Context Window** | Expand surrounding chunk context after retrieval |
| **Document Summarization** | Auto-generate document summaries |
| **Chunk Enrichment** | LLM-enhanced chunk semantics (optional) |

### Knowledge Base Configuration Example

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

See `docs/phase2.md` for more configuration examples.

---

## Project Structure

```
RAGForge/
├── app/                      # Application code
│   ├── main.py              # FastAPI entry
│   ├── config.py            # Configuration management
│   ├── api/                 # API routes
│   │   ├── deps.py          # Dependency injection
│   │   └── routes/          # Feature routes
│   ├── auth/                # Authentication
│   │   └── api_key.py       # API Key auth & rate limiting
│   ├── security/            # Security module
│   │   ├── credential_manager.py   # Credential manager
│   │   └── credential_scanner.py   # Credential scanner
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── ingestion.py     # Document ingestion
│   │   ├── query.py         # Retrieval service
│   │   ├── rag.py           # RAG generation
│   │   └── acl.py           # ACL permission service
│   ├── pipeline/            # Algorithm framework
│   │   ├── base.py          # Base protocols
│   │   ├── registry.py      # Algorithm registry
│   │   ├── chunkers/        # Chunkers
│   │   ├── retrievers/      # Retrievers
│   │   ├── indexers/        # Indexers (RAPTOR)
│   │   ├── query_transforms/ # Query transforms
│   │   ├── enrichers/       # Document enrichers
│   │   └── postprocessors/  # Postprocessors
│   ├── infra/               # Infrastructure
│   │   ├── llm.py           # LLM client
│   │   ├── embeddings.py    # Embeddings
│   │   ├── rerank.py        # Reranking module
│   │   ├── vector_store.py  # Qdrant operations
│   │   ├── bm25_store.py    # BM25 storage
│   │   └── llamaindex.py    # LlamaIndex integration
│   ├── middleware/          # Middleware
│   │   ├── audit.py         # Audit logging
│   │   └── request_trace.py # Request tracing
│   └── db/                  # Database config
├── frontend/                # Next.js frontend
├── sdk/                     # Python SDK
├── alembic/                 # Database migrations
├── scripts/                 # Utility scripts
├── tests/                   # Test files
├── docs/                    # VitePress documentation
├── docker-compose.yml       # Docker compose
├── Dockerfile               # Docker image
├── pyproject.toml           # Project config
└── AGENTS.md                # AI assistant guide
```

---

## Development Guide

### Running Tests

```bash
# Unit tests
uv run pytest tests/ -v

# End-to-end tests (requires running service)
API_KEY="your_key" API_BASE="http://localhost:8020" uv run pytest test/test_live_e2e.py -v

# Type checking
uv run mypy app/

# Code formatting
uv run ruff format .
uv run ruff check --fix .
```

### Database Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "description"

# Run migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1
```

### Adding New Features

1. **Add new chunker**: See `app/pipeline/chunkers/AGENTS.md`
2. **Add new retriever**: See `app/pipeline/retrievers/AGENTS.md`
3. **Add new API**: See `app/api/AGENTS.md`
4. **Add new model**: See `app/models/AGENTS.md`

---

## Deployment

### Docker Deployment

```bash
# Build image (use host network for speed)
docker build --network=host -t ragforge-api .

# Start services
docker compose up -d

# View logs
docker compose logs -f api
```

### Production Recommendations

1. **Security**
   - Enable HTTPS (use Nginx reverse proxy)
   - Rotate API Keys regularly
   - Configure firewall rules

2. **Performance**
   - Adjust `API_RATE_LIMIT_PER_MINUTE` rate limiting
   - Use Redis for rate limiting
   - Configure connection pool size

3. **High Availability**
   - PostgreSQL primary-replica replication
   - Qdrant cluster mode
   - Multi-instance deployment + load balancing

4. **Monitoring**
   - Integrate Prometheus + Grafana
   - Configure log collection (ELK)
   - Set up alerting rules

---

## Documentation

Complete VitePress documentation site:

| Category | Description | Link |
|----------|-------------|------|
| **Getting Started** | Installation, configuration, first API call | [docs/getting-started/](./docs/getting-started/) |
| **Guides** | Environment config, deployment, SDK usage | [docs/guides/](./docs/guides/) |
| **Architecture** | System design, Pipeline architecture, API specs | [docs/architecture/](./docs/architecture/) |
| **Development** | Contributing guide, testing, troubleshooting | [docs/development/](./docs/development/) |
| **Operations** | Deployment, monitoring, security | [docs/operations/](./docs/operations/) |
| **Security Guide** | Credential management, threat model, auditing | [docs/SECURITY.md](./docs/SECURITY.md) |

### Quick Links

- 📖 **[Documentation Index](./docs/documentation.md)** - Complete doc navigation
- 🚀 **[Quick Start](./docs/getting-started/quick-start.md)** - Get started in 5 minutes
- 🔌 **[OpenAI SDK Guide](./docs/guides/openai-sdk.md)** - OpenAI-compatible API
- 🐍 **[Python SDK](./sdk/README.md)** - SDK documentation
- 🏗️ **[Architecture](./docs/ARCHITECTURE.md)** - System architecture overview

---

## License

MIT License

---

## Contributing

Welcome to submit Issues and Pull Requests!

Please read before contributing:
- **[CONTRIBUTING.md](./docs/CONTRIBUTING.md)** - Contribution guide
- **[AGENTS.md](./AGENTS.md)** - AI assistant development guide
- **[docs/development/](./docs/development/)** - Development docs
