# 配置指南

本指南详细介绍 Self-RAG Pipeline 的配置选项，帮助您根据需求优化系统性能。

## 配置文件

系统使用环境变量进行配置，主要配置文件：

- `.env` - 主配置文件
- `.env.example` - 配置模板
- `docker-compose.yml` - Docker 服务配置

## 核心配置

### 应用基础配置

```bash
# 运行环境
ENVIRONMENT=dev  # dev/staging/prod

# API 服务配置
API_HOST=0.0.0.0
API_PORT=8020

# 管理员令牌（必需）
ADMIN_TOKEN=your-secure-admin-token-here
```

### 数据库配置

```bash
# PostgreSQL 连接字符串
DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 连接池配置
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

### 向量存储配置

#### Qdrant 配置

```bash
# Qdrant 服务地址
QDRANT_URL=http://localhost:6333

# Qdrant API Key（云服务使用）
QDRANT_API_KEY=

# Collection 配置
QDRANT_COLLECTION_PREFIX=kb_

# 多租户隔离策略
QDRANT_ISOLATION_STRATEGY=auto  # partition/collection/auto
QDRANT_SHARED_COLLECTION=kb_shared
ISOLATION_AUTO_THRESHOLD=10000
```

**隔离策略说明**：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `partition` | 共享 Collection，按 tenant_id 过滤 | 小规模租户，节省资源 |
| `collection` | 每租户独立 Collection | 大规模租户，性能隔离 |
| `auto` | 自动选择策略 | 根据数据量自动优化 |

#### 可选向量存储

**Milvus 配置**：
```bash
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USERNAME=
MILVUS_PASSWORD=
```

**Elasticsearch 配置**：
```bash
ES_HOSTS=http://localhost:9200
ES_USERNAME=
ES_PASSWORD=
ES_INDEX_PREFIX=kb_
ES_REQUEST_TIMEOUT=10
```

### 稀疏检索配置

```bash
# 启用 BM25 稀疏检索
BM25_ENABLED=true

# BM25 后端选择
BM25_BACKEND=memory  # memory/es

# Elasticsearch 配置（当 BM25_BACKEND=es 时）
ES_HOSTS=http://localhost:9200
ES_INDEX_MODE=shared  # shared/per_kb
ES_BULK_BATCH_SIZE=500
ES_ANALYZER=standard
```

## 模型提供商配置

### LLM 配置

```bash
# LLM 提供商
LLM_PROVIDER=ollama  # ollama/openai/gemini/qwen/deepseek/zhipu/siliconflow

# LLM 模型
LLM_MODEL=qwen3:14b

# LLM 参数
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

### Embedding 配置

```bash
# Embedding 提供商
EMBEDDING_PROVIDER=ollama  # ollama/openai/gemini/qwen/deepseek/zhipu/siliconflow

# Embedding 模型
EMBEDDING_MODEL=bge-m3

# 向量维度
EMBEDDING_DIM=1024
```

### Rerank 配置

```bash
# Rerank 提供商
RERANK_PROVIDER=none  # none/ollama/cohere/zhipu/siliconflow

# Rerank 模型
RERANK_MODEL=

# Rerank 参数
RERANK_TOP_K=10
```

### 提供商 API Keys

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Google Gemini
GEMINI_API_KEY=AIzaSy-your-gemini-key

# 阿里云通义千问
QWEN_API_KEY=sk-your-qwen-key

# 月之暗面 Kimi
KIMI_API_KEY=sk-your-kimi-key

# DeepSeek
DEEPSEEK_API_KEY=sk-your-deepseek-key

# 智谱 AI
ZHIPU_API_KEY=your-zhipu-key

# SiliconFlow
SILICONFLOW_API_KEY=sk-your-siliconflow-key

# Cohere (Rerank)
COHERE_API_KEY=your-cohere-key
```

## 认证与权限配置

### API Key 配置

```bash
# API Key 前缀
API_KEY_PREFIX=kb_sk_

# 限流配置
API_RATE_LIMIT_PER_MINUTE=120

# API Key 过期时间（天）
API_KEY_DEFAULT_EXPIRY_DAYS=365
```

### 权限配置

```bash
# 默认角色权限
DEFAULT_API_KEY_ROLE=read  # admin/write/read

# 敏感度级别
DEFAULT_SENSITIVITY_LEVEL=public  # public/restricted
```

## 日志与监控配置

### 日志配置

```bash
# 日志级别
LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR

# 日志格式
LOG_JSON=false  # true=JSON格式，false=控制台格式

# 日志文件（可选）
LOG_FILE=
```

### 监控配置

```bash
# 启用指标收集
METRICS_ENABLED=true

# 指标保留时间（秒）
METRICS_RETENTION_SECONDS=3600
```

## 性能优化配置

### 并发配置

```bash
# Uvicorn Workers
UVICORN_WORKERS=1

# 异步并发限制
MAX_CONCURRENT_REQUESTS=100
```

### 缓存配置

```bash
# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# 缓存过期时间
CACHE_TTL_SECONDS=3600
```

### 请求限制

```bash
# 请求体大小限制（MB）
MAX_REQUEST_SIZE_MB=100

# 文档上传大小限制（MB）
MAX_DOCUMENT_SIZE_MB=50

# 批量操作限制
MAX_BATCH_SIZE=1000
```

## 算法配置

### 默认切分器配置

```bash
# 默认切分器
DEFAULT_CHUNKER=sliding_window

# 切分参数
DEFAULT_CHUNK_SIZE=1024
DEFAULT_CHUNK_OVERLAP=100
```

### 默认检索器配置

```bash
# 默认检索器
DEFAULT_RETRIEVER=hybrid

# 检索参数
DEFAULT_TOP_K=5
DEFAULT_SCORE_THRESHOLD=0.0

# 混合检索权重
HYBRID_DENSE_WEIGHT=0.7
HYBRID_SPARSE_WEIGHT=0.3
```

## 开发环境配置

### 调试配置

```bash
# 启用调试模式
DEBUG=true

# 启用热重载
RELOAD=true

# 跨域配置
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3003"]
```

### 测试配置

```bash
# 测试数据库
TEST_DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb_test

# 测试 API Key
TEST_API_KEY=kb_sk_test_key
```

## 生产环境配置

### 安全配置

```bash
# 生产环境标识
ENVIRONMENT=prod

# 禁用调试
DEBUG=false
RELOAD=false

# 安全头配置
SECURE_HEADERS=true

# HTTPS 重定向
FORCE_HTTPS=true
```

### 性能配置

```bash
# 生产级连接池
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# 多 Worker
UVICORN_WORKERS=4

# 启用 JSON 日志
LOG_JSON=true
LOG_LEVEL=INFO
```

## 配置验证

### 检查配置

```bash
# 检查配置文件语法
uv run python -c "from app.config import get_settings; print('配置验证通过')"

# 检查数据库连接
uv run python -c "
import asyncio
from app.db.session import test_connection
asyncio.run(test_connection())
"

# 检查向量库连接
curl http://localhost:6333/collections
```

### 常见配置错误

1. **数据库连接失败**
   - 检查 `DATABASE_URL` 格式
   - 确认数据库服务运行状态

2. **向量库连接失败**
   - 检查 `QDRANT_URL` 地址
   - 确认 Qdrant 服务状态

3. **模型 API 调用失败**
   - 检查 API Key 格式和有效性
   - 确认网络连接和代理设置

## 配置最佳实践

### 安全实践

1. **敏感信息管理**
   - 使用环境变量存储 API Keys
   - 不要将 `.env` 文件提交到版本控制
   - 定期轮换 API Keys 和管理员令牌

2. **权限最小化**
   - 为不同用途创建不同权限的 API Key
   - 使用 `scope_kb_ids` 限制访问范围
   - 定期审查和清理无用的 API Key

### 性能实践

1. **资源配置**
   - 根据并发需求调整连接池大小
   - 监控内存使用，适当调整 Worker 数量
   - 使用 Redis 缓存提升性能

2. **存储优化**
   - 大规模部署使用 Collection 隔离策略
   - 定期清理过期数据和日志
   - 监控存储空间使用情况

### 监控实践

1. **日志管理**
   - 生产环境使用 JSON 格式日志
   - 配置日志轮转和归档
   - 集成 ELK 或其他日志分析系统

2. **指标监控**
   - 监控 API 响应时间和错误率
   - 跟踪模型调用次数和成本
   - 设置关键指标告警

## 下一步

配置完成后，您可以：

1. 查看[快速开始](quick-start.md)学习基本使用
2. 阅读[第一个 API 调用](first-api-call.md)了解 API 使用
3. 参考[部署指南](../operations/deployment.md)进行生产部署