# 环境配置文件使用指南

## 配置文件结构

```
.env.example  → 配置模板（包含所有选项和详细说明）✅ 提交到 Git
.env          → Docker/生产环境默认配置            🔒 已忽略
.env.local    → 本地开发覆盖配置（包含真实密钥）    🔒 已忽略
```

## 文件说明

### 1. `.env.example` - 配置模板

- **用途**：配置文档和模板
- **内容**：所有可用的配置项 + 详细说明 + 占位符值
- **Git**：✅ 提交到版本控制
- **更新**：添加新配置项时更新此文件

### 2. `.env` - Docker/生产环境配置

- **用途**：Docker Compose 和生产环境的默认配置
- **内容**：容器间通信地址、默认值、占位符密钥
- **Git**：🔒 已忽略（当前配置）
- **特点**：
  - 数据库地址：`db:5432`（容器内通信）
  - Redis 地址：`redis:6379`（容器内通信）
  - Ollama 地址：`host.docker.internal:11434`（访问宿主机）

### 3. `.env.local` - 本地开发配置

- **用途**：本地开发时覆盖 `.env` 中的配置
- **内容**：真实的 API 密钥、本地服务地址
- **Git**：🔒 已忽略（必须）
- **特点**：
  - 数据库地址：`localhost:5435`（宿主机访问容器）
  - Redis 地址：`localhost:6389`（宿主机访问容器）
  - Ollama 地址：`localhost:11434`（本地服务）
  - 包含真实的 API Keys

## 使用场景

### 场景 1：Docker Compose 部署

```bash
# 使用 .env 文件（容器间通信配置）
docker compose up -d

# 配置加载优先级：.env
```

**特点**：
- 所有服务在 Docker 网络内通信
- 使用服务名（db、redis）作为主机名
- 端口使用容器内部端口

### 场景 2：本地开发（Python 脚本）

```bash
# 使用 .env.local 覆盖配置（宿主机访问）
uv run uvicorn app.main:app --reload --port 8020

# 配置加载优先级：.env.local > .env
```

**特点**：
- 数据库/Redis 通过映射端口访问（5435/6389）
- 使用 localhost 作为主机名
- 包含真实的 API 密钥

### 场景 3：新成员初始化

```bash
# 1. 复制模板
cp .env.example .env.local

# 2. 修改 .env.local 中的配置
# - 填入真实的 API Keys
# - 调整服务地址为 localhost（本地开发）
# - 设置管理员 Token

# 3. 启动基础设施
docker compose up -d db redis

# 4. 运行数据库迁移
uv run alembic upgrade head

# 5. 启动 API 服务
uv run uvicorn app.main:app --reload --port 8020
```

## 配置项分类

### 🔧 基础配置
- `APP_NAME`：应用名称
- `ENVIRONMENT`：运行环境（dev/staging/production）
- `DATABASE_URL`：PostgreSQL 连接地址
- `API_KEY_PREFIX`：API 密钥前缀

### 🚦 限流配置
- `API_RATE_LIMIT_PER_MINUTE`：每分钟请求限制
- `REDIS_URL`：Redis 连接地址（用于分布式限流）

### 💾 向量存储
- `VECTOR_STORE=postgresql`：使用 PostgreSQL + pgvector

### 📦 Redis 缓存
- `REDIS_CACHE_ENABLED`：是否启用查询缓存
- `REDIS_CACHE_TTL`：缓存过期时间（秒）
- `REDIS_CONFIG_CACHE_TTL`：配置缓存时间（秒）

### 🤖 模型配置
- **LLM**：`LLM_PROVIDER`、`LLM_MODEL`
- **Embedding**：`EMBEDDING_PROVIDER`、`EMBEDDING_MODEL`
- **Rerank**：`RERANK_PROVIDER`、`RERANK_MODEL`

### 🔑 API 密钥
- `OLLAMA_BASE_URL`：Ollama 服务地址（无需 Key）
- `OPENAI_API_KEY`：OpenAI API 密钥
- `GEMINI_API_KEY`：Google Gemini 密钥
- `QWEN_API_KEY`：阿里云通义千问密钥
- `ADMIN_TOKEN`：管理员 API Token

### 📊 日志配置
- `LOG_LEVEL`：日志级别（DEBUG/INFO/WARNING/ERROR）
- `TIMEZONE`：时区设置

## 安全最佳实践

### ✅ 应该做的

1. **使用强随机 Token**
   ```bash
   # 生成安全的 ADMIN_TOKEN
   openssl rand -base64 32
   ```

2. **分离敏感配置**
   - 真实 API 密钥只放在 `.env.local`
   - `.env` 使用占位符

3. **定期轮换密钥**
   - API Keys 定期更换
   - ADMIN_TOKEN 定期重置

4. **最小权限原则**
   - 生产环境使用独立的 API Keys
   - 测试环境使用受限权限的 Keys

### ❌ 不应该做的

1. ❌ 将 `.env.local` 提交到 Git
2. ❌ 在 `.env` 中包含真实密钥
3. ❌ 在代码或注释中硬编码密钥
4. ❌ 在公共渠道分享配置文件截图

## 端口映射说明

| 服务 | 容器端口 | 宿主机端口 | 用途 |
|------|---------|-----------|------|
| PostgreSQL | 5432 | 5435 | 数据库 |
| Redis | 6379 | 6389 | 缓存/限流 |
| API | 8020 | 8020 | API 服务 |
| Frontend | 3000 | 3003 | 前端界面 |
| Ollama | 11434 | 11434 | LLM 服务 |

## 配置优先级

```
环境变量 > .env.local > .env > .env.example
```

FastAPI 使用 `python-dotenv` 加载配置，遵循以下规则：

1. 系统环境变量优先级最高
2. `.env.local` 覆盖 `.env`
3. `.env.example` 仅作为文档

## 故障排查

### 问题：容器无法连接数据库

**症状**：`connection refused` 或 `could not connect to server`

**检查**：
```bash
# 1. 确认使用正确的配置文件
docker compose config

# 2. 检查容器网络
docker network inspect self_rag_pipeline_default

# 3. 验证环境变量
docker compose exec api env | grep DATABASE_URL
```

**解决**：确保 `.env` 使用容器服务名（db:5432）

### 问题：本地开发无法连接数据库

**症状**：运行 `uv run uvicorn` 时无法连接

**检查**：
```bash
# 1. 确认容器运行中
docker compose ps

# 2. 测试端口连通性
nc -zv localhost 5435
nc -zv localhost 6389

# 3. 检查配置文件
cat .env.local | grep DATABASE_URL
```

**解决**：确保 `.env.local` 使用 localhost 和映射端口（5435/6389）

### 问题：API 密钥无效

**症状**：`Invalid API key` 或 `Authentication failed`

**检查**：
```bash
# 1. 验证密钥格式
echo $QWEN_API_KEY | wc -c

# 2. 检查是否正确加载
uv run python -c "from app.config import settings; print(settings.QWEN_API_KEY)"
```

**解决**：
1. 确认 `.env.local` 中的密钥正确
2. 确认密钥未过期
3. 确认没有多余空格或引号

## 配置更新 Checklist

当添加新的配置项时：

- [ ] 在 `.env.example` 中添加详细说明
- [ ] 在 `.env` 中添加占位符或默认值
- [ ] 在 `.env.local` 中添加真实值（如需要）
- [ ] 更新 `app/config.py` 中的配置类
- [ ] 更新本文档
- [ ] 通知团队成员更新其本地配置

## 常见配置组合

### 组合 1：完全本地开发（Ollama）

```bash
# .env.local
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
RERANK_PROVIDER=ollama
RERANK_MODEL=bge-reranker-large
OLLAMA_BASE_URL=http://localhost:11434
```

**特点**：无需外部 API 密钥，完全离线

### 组合 2：云端模型（通义千问）

```bash
# .env.local
LLM_PROVIDER=qwen
LLM_MODEL=qwen-plus
EMBEDDING_PROVIDER=qwen
EMBEDDING_MODEL=text-embedding-v3
QWEN_API_KEY=sk-your_real_key_here
```

**特点**：高性能，需要网络和 API 密钥

### 组合 3：混合模式（推荐）

```bash
# .env.local
# 使用云端 LLM（质量高）
LLM_PROVIDER=qwen
LLM_MODEL=qwen-plus
QWEN_API_KEY=sk-your_key

# 使用本地 Embedding（快速+省钱）
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3

# 使用本地 Rerank
RERANK_PROVIDER=ollama
RERANK_MODEL=bge-reranker-large
```

**特点**：平衡性能、成本和速度

---

**最后更新**：2026-01-15
**维护者**：项目团队
