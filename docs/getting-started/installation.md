# 安装指南

本指南将帮助您快速安装和配置 Self-RAG Pipeline 服务。

## 系统要求

### 硬件要求

| 组件 | 最小配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4+ 核 |
| 内存 | 4 GB | 8+ GB |
| 存储 | 20 GB SSD | 100+ GB SSD |

### 软件要求

- **Python**: 3.11+
- **Docker**: 24.0+
- **Docker Compose**: 2.0+
- **uv**: 推荐使用 [uv](https://github.com/astral-sh/uv) 作为依赖管理工具

## 安装方式

### 方式一：Docker Compose（推荐）

这是最简单的安装方式，适合快速体验和生产部署。

```bash
# 1. 克隆项目
git clone <repo-url>
cd self_rag_pipeline

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的配置

# 3. 启动所有服务
docker compose up -d

# 4. 执行数据库迁移
docker compose exec api uv run alembic upgrade head

# 5. 检查服务状态
curl http://localhost:8020/health
```

### 方式二：本地开发环境

适合开发者进行代码开发和调试。

```bash
# 1. 安装 Python 依赖管理工具 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或使用 pip: pip install uv

# 2. 克隆项目并安装依赖
git clone <repo-url>
cd self_rag_pipeline
uv sync

# 3. 启动基础设施服务
docker compose up -d db qdrant

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 5. 执行数据库迁移
uv run alembic upgrade head

# 6. 启动开发服务器
uv run uvicorn app.main:app --reload --port 8020
```

### 方式三：验证 OpenSearch 稀疏检索（可选）

如果需要使用 Elasticsearch/OpenSearch 作为稀疏检索后端：

```bash
# 启动带 OpenSearch 的完整环境
docker compose -f docker-compose.opensearch.yml up -d

# 配置稀疏检索
export BM25_ENABLED=true
export BM25_BACKEND=es
export ES_HOSTS=http://localhost:9200

# 执行数据库迁移
uv run alembic upgrade head

# 启动服务
uv run uvicorn app.main:app --reload --port 8020
```

## 环境变量配置

### 必需配置

编辑 `.env` 文件，设置以下必需的环境变量：

```bash
# 管理员令牌（用于创建租户）
ADMIN_TOKEN=your-secure-admin-token-here

# 数据库连接
DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 向量库连接
QDRANT_URL=http://localhost:6333

# LLM 配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:14b

# Embedding 配置
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
```

### 可选配置

```bash
# API Key 配置
API_KEY_PREFIX=kb_sk_
API_RATE_LIMIT_PER_MINUTE=120

# 日志配置
LOG_LEVEL=INFO
LOG_JSON=false

# Rerank 配置（可选）
RERANK_PROVIDER=none
```

## 验证安装

### 1. 检查服务健康状态

```bash
# 存活检查
curl http://localhost:8020/health
# 预期返回: {"status": "ok"}

# 就绪检查（检查数据库和向量库连接）
curl http://localhost:8020/ready
# 预期返回: {"status": "ok", "checks": {...}}

# 系统指标
curl http://localhost:8020/metrics
```

### 2. 创建第一个租户

```bash
# 使用管理员 API 创建租户
curl -X POST "http://localhost:8020/admin/tenants" \
  -H "X-Admin-Token: your-secure-admin-token-here" \
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

### 3. 运行端到端测试

```bash
# 设置环境变量
export API_KEY="上面获取的 API Key"
export API_BASE="http://localhost:8020"

# 运行测试
uv run pytest test/test_live_e2e.py -v
```

## 常见问题

### 端口冲突

如果遇到端口冲突，可以修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  api:
    ports:
      - "8021:8020"  # 改为其他端口
```

### 数据库连接失败

检查 PostgreSQL 服务是否正常启动：

```bash
docker compose logs db
```

### 向量库连接失败

检查 Qdrant 服务状态：

```bash
docker compose logs qdrant
curl http://localhost:6333/collections
```

### 权限问题

确保 Docker 有足够权限访问项目目录，特别是在 Linux 系统上。

## 下一步

安装完成后，您可以：

1. 阅读[配置指南](configuration.md)了解详细配置选项
2. 查看[快速开始](quick-start.md)学习基本使用方法
3. 尝试[第一个 API 调用](first-api-call.md)

## 卸载

如果需要完全卸载服务：

```bash
# 停止并删除容器
docker compose down -v

# 删除镜像（可选）
docker rmi $(docker images "self_rag_pipeline*" -q)

# 删除项目目录
cd ..
rm -rf self_rag_pipeline
```