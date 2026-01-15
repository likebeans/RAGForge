# 部署指南

本文档介绍如何在生产环境部署 Self-RAG Pipeline 服务。

## 系统要求

### 硬件要求

| 组件 | 最小配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4+ 核 |
| 内存 | 4 GB | 8+ GB |
| 存储 | 20 GB SSD | 100+ GB SSD |

### 软件要求

- Docker 24.0+
- Docker Compose 2.0+
- （可选）Kubernetes 1.25+

## 快速部署

### 1. 准备环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
vim .env
```

关键配置：

```bash
# 数据库（必需）
DATABASE_URL=postgresql+asyncpg://kb:kb@db:5432/kb

# 向量库（必需）
QDRANT_URL=http://qdrant:6333

# 管理员 Token（必需，用于租户管理）
ADMIN_TOKEN=your-secure-admin-token-here

# LLM 配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:14b

# Embedding 配置
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
```

### 2. 启动服务

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f api

# 运行数据库迁移
docker compose exec api alembic upgrade head
```

### 3. 验证部署

```bash
# 健康检查
curl http://localhost:8020/health
# 预期返回: {"status": "ok"}

# 就绪检查
curl http://localhost:8020/ready
# 预期返回: {"status": "ok", "checks": {...}}

# 创建首个租户
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: your-secure-admin-token-here" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-company"}'
```

## Docker Compose 部署

### 完整配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8020:8020"
    environment:
      - DATABASE_URL=postgresql+asyncpg://kb:kb@db:5432/kb
      - QDRANT_URL=http://qdrant:6333
      - ADMIN_TOKEN=${ADMIN_TOKEN}
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - LLM_MODEL=${LLM_MODEL:-qwen3:14b}
      - EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-ollama}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-bge-m3}
      - EMBEDDING_DIM=${EMBEDDING_DIM:-1024}
    depends_on:
      db:
        condition: service_healthy
      qdrant:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=kb
      - POSTGRES_PASSWORD=kb
      - POSTGRES_DB=kb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kb"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  # 可选：本地 Ollama
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

volumes:
  postgres_data:
  qdrant_data:
  ollama_data:
```

## Kubernetes 部署

### 1. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-pipeline-config
data:
  LLM_PROVIDER: "ollama"
  LLM_MODEL: "qwen3:14b"
  EMBEDDING_PROVIDER: "ollama"
  EMBEDDING_MODEL: "bge-m3"
  EMBEDDING_DIM: "1024"
```

### 2. Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-pipeline-secret
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://kb:kb@postgres:5432/kb"
  QDRANT_URL: "http://qdrant:6333"
  ADMIN_TOKEN: "your-secure-admin-token"
```

### 3. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-pipeline-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: rag-pipeline-api
  template:
    metadata:
      labels:
        app: rag-pipeline-api
    spec:
      containers:
      - name: api
        image: your-registry/self_rag_pipeline-api:latest
        ports:
        - containerPort: 8020
        envFrom:
        - configMapRef:
            name: rag-pipeline-config
        - secretRef:
            name: rag-pipeline-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8020
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8020
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
```

### 4. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-pipeline-api
spec:
  selector:
    app: rag-pipeline-api
  ports:
  - port: 8020
    targetPort: 8020
  type: ClusterIP
```

## 运维接口

### 健康检查

| 端点 | 用途 | 响应码 |
|------|------|--------|
| `GET /health` | 存活探测 (Liveness) | 200 |
| `GET /ready` | 就绪探测 (Readiness) | 200/503 |
| `GET /metrics` | 系统指标 | 200 |

### 就绪检查响应

```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "message": "connected"},
    "qdrant": {"status": "ok", "message": "connected (5 collections)"}
  },
  "timestamp": "2024-12-04T03:00:00.000Z"
}
```

### 指标响应

```json
{
  "service": {
    "uptime_seconds": 3600.5,
    "uptime_human": "1h 0m 0s",
    "timestamp": "2024-12-04T03:00:00.000Z"
  },
  "config": {
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "embedding_dim": 1024
  },
  "stats": {
    "calls": {
      "llm:ollama": {"count": 150, "avg_latency_ms": 1200},
      "embedding:ollama": {"count": 500, "avg_latency_ms": 50}
    },
    "retrievals": {
      "hybrid": {"count": 200},
      "dense": {"count": 100}
    }
  }
}
```

## 性能调优

### 数据库连接池

在 `app/db/session.py` 中配置：

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,           # 基础连接数
    max_overflow=20,        # 最大额外连接
    pool_timeout=30,        # 获取连接超时
    pool_recycle=1800,      # 连接回收时间
)
```

### Uvicorn Workers

```bash
# 生产环境启动（多 worker）
uvicorn app.main:app --host 0.0.0.0 --port 8020 --workers 4
```

### 资源建议

| 并发量 | Workers | 内存 | CPU |
|--------|---------|------|-----|
| < 50 | 2 | 2 GB | 2 核 |
| 50-200 | 4 | 4 GB | 4 核 |
| > 200 | 8+ | 8+ GB | 8+ 核 |

## 安全配置

### 1. HTTPS

使用反向代理（Nginx/Traefik）配置 TLS：

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/api.crt;
    ssl_certificate_key /etc/ssl/private/api.key;
    
    location / {
        proxy_pass http://localhost:8020;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

### 2. 网络隔离

- 数据库和向量库不暴露公网端口
- API 服务仅通过反向代理访问
- 使用 Docker 网络或 K8s NetworkPolicy 隔离

### 3. 密钥管理

- 使用环境变量或 Secret 管理敏感配置
- 不在代码或镜像中硬编码密钥
- 定期轮换 ADMIN_TOKEN 和 API Key

## 监控与日志

### 日志格式

服务输出 JSON 格式日志，便于 ELK/Loki 聚合：

```json
{
  "timestamp": "2024-12-04T03:00:00.000Z",
  "level": "INFO",
  "logger": "app.services.query",
  "message": "[RETRIEVAL] hybrid 检索完成: 5 结果",
  "request_id": "abc123",
  "tenant_id": "tenant_001"
}
```

### Prometheus 集成

可通过 `/metrics` 端点接入 Prometheus（需自定义格式转换）。

### 告警建议

| 指标 | 阈值 | 说明 |
|------|------|------|
| `/ready` 返回 503 | 持续 1 分钟 | 服务不可用 |
| 检索 P99 延迟 | > 5s | 性能下降 |
| 错误率 | > 5% | 服务异常 |

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查 DATABASE_URL 配置
   - 确认 PostgreSQL 服务运行中
   - 检查网络连通性

2. **向量库连接失败**
   - 检查 QDRANT_URL 配置
   - 确认 Qdrant 服务运行中

3. **Embedding 超时**
   - 检查 Ollama/远程服务状态
   - 考虑增加超时时间或使用本地模型

### 日志查看

```bash
# Docker Compose
docker compose logs -f api

# Kubernetes
kubectl logs -f deployment/rag-pipeline-api
```

## 备份与恢复

### PostgreSQL 备份

```bash
# 备份
docker compose exec db pg_dump -U kb kb > backup.sql

# 恢复
docker compose exec -T db psql -U kb kb < backup.sql
```

### Qdrant 备份

Qdrant 数据存储在 volume 中，定期备份 `qdrant_data` 目录即可。

---

如有问题，请参考 `docs/开发.md` 或提交 Issue。
