# 架构更新总结

**更新日期**：2026-01-15

## 📋 更新内容

### 1. Docker Compose 配置

#### `docker-compose.yml` (主配置)
- ✅ 添加 Redis 服务（`redis:7-alpine`）
- ✅ 移除 Qdrant 服务
- ✅ 更新 API 服务环境变量
  - 移除：`QDRANT_URL`
  - 新增：`REDIS_URL`、`VECTOR_STORE=postgresql`
- ✅ 更新端口映射：Redis `6389:6379`

#### `docker-compose.opensearch.yml` (生产配置)
- ✅ 添加 Redis 服务（端口 `6390:6379`）
- ✅ 移除 Qdrant 服务
- ✅ 更新服务顺序（db → redis → opensearch → api → frontend）
- ✅ 更新端口映射避免冲突
  - PostgreSQL: `5436:5432`
  - Redis: `6390:6379`
  - API: `8021:8020`
  - Frontend: `3004:3000`
- ✅ 添加 OpenSearch 数据持久化卷
- ✅ 更新 API 环境变量配置

### 2. 环境配置文件

#### `.env.example` (配置模板)
- ✅ 添加详细的配置说明和分类
- ✅ 移除 Qdrant 相关配置
- ✅ 新增向量存储配置：`VECTOR_STORE=postgresql`
- ✅ 新增完整的 Redis 配置项
- ✅ 更新模型提供商配置说明
- ✅ 调整配置项顺序和分组

#### `.env` (Docker 默认配置)
- ✅ 移除 Qdrant 配置
- ✅ 添加 Redis 配置
- ✅ 添加向量存储配置
- ✅ 更新 OpenAI 配置（使用 Ollama 兼容接口）

#### `.env.local` (本地开发配置)
- ✅ 移除 Qdrant 配置
- ✅ 更新 Redis URL 为本地开发地址
- ✅ 保留真实 API 密钥配置

### 3. 配置指南文档

#### `ENV_CONFIG_GUIDE.md` (新增)
- ✅ 环境文件结构说明
- ✅ 使用场景详细说明（Docker/本地开发/新成员初始化）
- ✅ 配置项完整分类和说明
- ✅ 安全最佳实践
- ✅ 故障排查指南
- ✅ 常见配置组合示例
- ✅ 端口映射对照表

### 4. README 文档

#### `README.md` (英文版)
- ✅ 更新快速开始部分（移除 Qdrant，添加 Redis）
- ✅ 新增"Configuration"章节
  - 环境文件结构说明
  - Docker Compose 配置对比
  - BM25 存储架构对比表
  - 端口映射对照表
- ✅ 更新架构图（PostgreSQL + Redis + OpenSearch + Milvus）
- ✅ 更新技术栈说明
  - 向量存储：PostgreSQL pgvector (默认)
  - 缓存 & 限流：Redis 7
  - BM25 存储：内存 (默认) / OpenSearch (生产)

#### `README.zh-CN.md` (中文版)
- ✅ 更新本地开发步骤（使用 `.env.local`）
- ✅ 移除旧的 OpenSearch 验证步骤
- ✅ 新增"环境文件结构"说明
- ✅ 新增"Docker Compose 配置"说明
- ✅ 新增"BM25 存储架构对比"表格
- ✅ 新增"端口映射"对照表
- ✅ 更新架构图（与英文版一致）
- ✅ 更新技术栈说明
- ✅ 更新环境变量表格
  - 移除：Qdrant 配置
  - 新增：Redis、向量存储配置
- ✅ 标记废弃配置项

## 🏗️ 架构变更说明

### 向量存储

**之前**：
```
Qdrant (向量存储) + PostgreSQL (元数据)
```

**现在**：
```
PostgreSQL (元数据 + pgvector 向量存储)
```

### BM25 存储

**主配置**：
```
PostgreSQL (chunks 持久化)
    ↓
内存 BM25 索引（启动时从 PostgreSQL 加载）
```

**OpenSearch 配置**：
```
PostgreSQL (chunks 持久化)
    ↓
OpenSearch (BM25 索引持久化)
```

### 完整技术栈

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
│    │ Metadata │  │ Cache &  │  │   BM25   │  │ (Vector) │      │
│    │ + Vector │  │RateLimit │  │(Optional)│  │(Optional)│      │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 配置对比

### 端口映射

| 服务 | 主配置 | OpenSearch 配置 | 说明 |
|------|--------|----------------|------|
| API | 8020 | 8021 | FastAPI 服务 |
| Frontend | 3003 | 3004 | Next.js 前端 |
| PostgreSQL | 5435 | 5436 | 数据库 |
| Redis | 6389 | 6390 | 缓存/限流 |
| OpenSearch | - | 9200 | BM25 索引 |

### BM25 存储方案对比

| 特性 | 主配置（内存） | OpenSearch 配置 |
|-----|--------------|----------------|
| **数据源** | PostgreSQL | PostgreSQL |
| **索引位置** | 内存 | OpenSearch |
| **持久化** | ❌ 索引重启丢失 | ✅ 持久化 |
| **重启恢复** | 需从 PG 重建 | 自动恢复 |
| **多副本一致性** | ❌ 各副本独立 | ✅ 共享索引 |
| **资源占用** | 低 | 高 |
| **适用场景** | 开发、小规模 | 生产、大规模 |

### 环境文件说明

| 文件 | 用途 | Git 状态 | 配置特点 |
|------|------|---------|---------|
| `.env.example` | 配置模板 | ✅ 提交 | 所有选项 + 详细说明 |
| `.env` | Docker 默认 | 🔒 忽略 | 容器间通信地址 |
| `.env.local` | 本地开发 | 🔒 忽略 | localhost 地址 + 真实密钥 |

## 🚀 使用方式

### 开发环境（主配置）

```bash
# 启动服务
docker compose up -d

# 访问
curl http://localhost:8020/health
open http://localhost:3003
```

### 生产环境（OpenSearch 配置）

```bash
# 启动服务
docker compose -f docker-compose.opensearch.yml up -d

# 访问
curl http://localhost:8021/health
open http://localhost:3004
```

### 本地开发

```bash
# 1. 启动基础设施
docker compose up -d db redis

# 2. 配置环境
cp .env.example .env.local
# 编辑 .env.local，填入真实配置

# 3. 运行迁移
uv run alembic upgrade head

# 4. 启动 API
uv run uvicorn app.main:app --reload --port 8020
```

## ⚠️ 迁移注意事项

### 对现有用户的影响

1. **Qdrant 数据迁移**
   - 如果之前使用 Qdrant 存储向量数据，需要重新入库
   - 现在使用 PostgreSQL + pgvector 存储

2. **环境变量更新**
   - 移除：`QDRANT_URL`、`QDRANT_API_KEY`
   - 新增：`REDIS_URL`、`VECTOR_STORE`

3. **端口变更**
   - Redis：6379 → 6389（避免冲突）
   - 需要更新本地开发配置

4. **配置文件分离**
   - 建议创建 `.env.local` 用于本地开发
   - 真实密钥不再放在 `.env` 中

### 升级步骤

```bash
# 1. 备份数据
docker compose exec db pg_dump -U kb kb > backup.sql

# 2. 停止旧服务
docker compose down

# 3. 更新配置文件
git pull
cp .env .env.backup
cp .env.example .env

# 4. 创建本地配置
cp .env.example .env.local
# 编辑 .env.local，填入真实配置

# 5. 启动新服务
docker compose up -d

# 6. 运行迁移
docker compose exec api uv run alembic upgrade head

# 7. 重新入库（如果使用了 Qdrant）
# 需要重新上传文档或使用迁移脚本
```

## 📖 相关文档

- **配置指南**：`ENV_CONFIG_GUIDE.md`
- **英文文档**：`README.md`
- **中文文档**：`README.zh-CN.md`
- **开发指南**：`AGENTS.md`
- **OpenAI SDK 说明**：`AGENTS_OPENAI_SDK.md`

## ✅ 验证清单

- [x] Docker Compose 配置更新
- [x] 环境配置文件标准化
- [x] README 文档更新（中英文）
- [x] 架构图更新
- [x] 技术栈说明更新
- [x] 端口映射文档化
- [x] BM25 存储方案说明
- [x] 配置指南创建
- [x] 迁移注意事项说明

---

**维护者**：项目团队  
**最后更新**：2026-01-15
