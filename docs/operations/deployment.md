# 部署运维指南

本文档详细介绍如何在生产环境部署和运维 Self-RAG Pipeline 服务。

## 系统要求

### 硬件配置

| 组件 | 最小配置 | 推荐配置 | 高负载配置 |
|------|----------|----------|------------|
| CPU | 2 核 | 4+ 核 | 8+ 核 |
| 内存 | 4 GB | 8+ GB | 16+ GB |
| 存储 | 20 GB SSD | 100+ GB SSD | 500+ GB NVMe |
| 网络 | 100 Mbps | 1 Gbps | 10 Gbps |

### 软件依赖

- **容器运行时**：Docker 24.0+ 或 Podman 4.0+
- **编排工具**：Docker Compose 2.0+ 或 Kubernetes 1.25+
- **操作系统**：Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- **Python**：3.11+ (如果源码部署)

### 外部服务

| 服务 | 版本要求 | 用途 |
|------|----------|------|
| PostgreSQL | 13+ | 元数据存储 |
| Qdrant | 1.7+ | 向量存储 |
| Redis | 6.0+ | 缓存和限流（可选） |
| Nginx/Traefik | 最新 | 反向代理和负载均衡 |

## 快速部署

### 1. 环境准备

```bash
# 创建部署目录
mkdir -p /opt/self-rag-pipeline
cd /opt/self-rag-pipeline

# 下载项目代码
git clone https://github.com/your-org/self-rag-pipeline.git .

# 复制环境变量模板
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，配置关键参数：

```bash
# 基础配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库配置（必需）
DATABASE_URL=postgresql+asyncpg://kb:kb@db:5432/kb

# 向量库配置（必需）
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_PREFIX=prod_

# 管理员认证（必需）
ADMIN_TOKEN=your-secure-admin-token-here

# LLM 配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:14b
OPENAI_API_KEY=sk-your-openai-key  # 如果使用 OpenAI

# Embedding 配置
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024

# 缓存和限流（推荐）
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_STORAGE=redis

# 安全配置
CORS_ORIGINS=https://your-frontend-domain.com
ALLOWED_HOSTS=api.your-domain.com
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker compose exec api alembic upgrade head

# 验证数据库连接
docker compose exec api python -c "
from app.db.session import async_session_maker
import asyncio
async def test():
    async with async_session_maker() as session:
        result = await session.execute('SELECT 1')
        print('Database connected:', result.scalar())
asyncio.run(test())
"
```

### 5. 验证部署

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
  -d '{"name": "default-tenant"}'
```

## Docker Compose 部署

### 完整配置文件

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: 
      context: .
      dockerfile: Dockerfile
    ports:
      - "8020:8020"
    environment:
      - DATABASE_URL=postgresql+asyncpg://kb:kb@db:5432/kb
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379/0
      - ADMIN_TOKEN=${ADMIN_TOKEN}
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - LLM_MODEL=${LLM_MODEL:-qwen3:14b}
      - EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-ollama}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-bge-m3}
      - EMBEDDING_DIM=${EMBEDDING_DIM:-1024}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    depends_on:
      db:
        condition: service_healthy
      qdrant:
        condition: service_started
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=kb
      - POSTGRES_PASSWORD=kb
      - POSTGRES_DB=kb
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kb -d kb"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    networks:
      - app-network

  qdrant:
    image: qdrant/qdrant:v1.7.4
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - app-network

  # 可选：本地 Ollama 服务
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - app-network

  # 可选：Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
  ollama_data:

networks:
  app-network:
    driver: bridge
```

### Nginx 配置

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8020;
    }

    # HTTP 重定向到 HTTPS
    server {
        listen 80;
        server_name api.your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS 配置
    server {
        listen 443 ssl http2;
        server_name api.your-domain.com;

        # SSL 证书
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        # SSL 安全配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # 安全头部
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
        add_header Referrer-Policy "strict-origin-when-cross-origin";

        # 请求体大小限制
        client_max_body_size 50M;

        # 代理配置
        location / {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
            
            # 超时配置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 健康检查端点
        location /health {
            proxy_pass http://api_backend/health;
            access_log off;
        }
    }
}
```

## Kubernetes 部署

### 1. Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: self-rag-pipeline
```

### 2. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-pipeline-config
  namespace: self-rag-pipeline
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  LLM_PROVIDER: "ollama"
  LLM_MODEL: "qwen3:14b"
  EMBEDDING_PROVIDER: "ollama"
  EMBEDDING_MODEL: "bge-m3"
  EMBEDDING_DIM: "1024"
  QDRANT_COLLECTION_PREFIX: "prod_"
  RATE_LIMIT_STORAGE: "redis"
```

### 3. Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-pipeline-secret
  namespace: self-rag-pipeline
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://kb:kb@postgres:5432/kb"
  QDRANT_URL: "http://qdrant:6333"
  REDIS_URL: "redis://redis:6379/0"
  ADMIN_TOKEN: "your-secure-admin-token"
  OPENAI_API_KEY: "sk-your-openai-key"
```

### 4. PostgreSQL 部署

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: self-rag-pipeline
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_USER
          value: "kb"
        - name: POSTGRES_PASSWORD
          value: "kb"
        - name: POSTGRES_DB
          value: "kb"
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - kb
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - kb
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: self-rag-pipeline
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### 5. Qdrant 部署

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: self-rag-pipeline
spec:
  serviceName: qdrant
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:v1.7.4
        ports:
        - containerPort: 6333
        - containerPort: 6334
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
        livenessProbe:
          httpGet:
            path: /health
            port: 6333
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 6333
          initialDelaySeconds: 10
          periodSeconds: 10
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
  volumeClaimTemplates:
  - metadata:
      name: qdrant-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: self-rag-pipeline
spec:
  selector:
    app: qdrant
  ports:
  - name: http
    port: 6333
    targetPort: 6333
  - name: grpc
    port: 6334
    targetPort: 6334
  type: ClusterIP
```

### 6. Redis 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: self-rag-pipeline
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--appendonly", "yes", "--maxmemory", "256mb", "--maxmemory-policy", "allkeys-lru"]
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
      volumes:
      - name: redis-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: self-rag-pipeline
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

### 7. API 服务部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-pipeline-api
  namespace: self-rag-pipeline
spec:
  replicas: 3
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
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8020
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: rag-pipeline-api
  namespace: self-rag-pipeline
spec:
  selector:
    app: rag-pipeline-api
  ports:
  - port: 8020
    targetPort: 8020
  type: ClusterIP
```

### 8. Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-pipeline-ingress
  namespace: self-rag-pipeline
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
spec:
  tls:
  - hosts:
    - api.your-domain.com
    secretName: rag-pipeline-tls
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rag-pipeline-api
            port:
              number: 8020
```

## 运维接口

### 健康检查

| 端点 | 用途 | 响应码 | 说明 |
|------|------|--------|------|
| `GET /health` | 存活探测 (Liveness) | 200 | 服务基本可用性 |
| `GET /ready` | 就绪探测 (Readiness) | 200/503 | 依赖服务就绪状态 |
| `GET /metrics` | 系统指标 | 200 | 运行时统计信息 |

### 就绪检查详情

```json
{
  "status": "ok",
  "checks": {
    "database": {
      "status": "ok", 
      "message": "connected",
      "latency_ms": 5.2
    },
    "qdrant": {
      "status": "ok", 
      "message": "connected (5 collections)",
      "latency_ms": 12.1
    },
    "redis": {
      "status": "ok",
      "message": "connected",
      "latency_ms": 1.8
    }
  },
  "timestamp": "2024-12-04T03:00:00.000Z"
}
```

### 系统指标

```json
{
  "service": {
    "uptime_seconds": 3600.5,
    "uptime_human": "1h 0m 0s",
    "timestamp": "2024-12-04T03:00:00.000Z",
    "version": "1.0.0",
    "environment": "production"
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
      "llm:ollama": {"count": 150, "avg_latency_ms": 1200, "error_rate": 0.02},
      "embedding:ollama": {"count": 500, "avg_latency_ms": 50, "error_rate": 0.01}
    },
    "retrievals": {
      "hybrid": {"count": 200, "avg_latency_ms": 300},
      "dense": {"count": 100, "avg_latency_ms": 150}
    },
    "database": {
      "active_connections": 8,
      "pool_size": 10,
      "avg_query_time_ms": 25
    }
  }
}
```

## 性能调优

### 数据库优化

#### 连接池配置

```python
# app/db/session.py
engine = create_async_engine(
    settings.database_url,
    pool_size=20,           # 基础连接数
    max_overflow=30,        # 最大额外连接
    pool_timeout=30,        # 获取连接超时
    pool_recycle=1800,      # 连接回收时间（30分钟）
    pool_pre_ping=True,     # 连接预检查
)
```

#### PostgreSQL 配置

```sql
-- postgresql.conf 优化
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### 应用服务优化

#### Uvicorn Workers

```bash
# 生产环境启动（多 worker）
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8020 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-log \
  --log-level info
```

#### 资源配置建议

| 并发量 | Workers | CPU | 内存 | 数据库连接池 |
|--------|---------|-----|------|-------------|
| < 50 | 2 | 2 核 | 2 GB | pool_size=10 |
| 50-200 | 4 | 4 核 | 4 GB | pool_size=15 |
| 200-500 | 8 | 8 核 | 8 GB | pool_size=20 |
| > 500 | 16+ | 16+ 核 | 16+ GB | pool_size=25+ |

### 向量库优化

#### Qdrant 配置

```yaml
# qdrant 配置优化
storage:
  # 使用 mmap 存储以节省内存
  storage_path: /qdrant/storage
  snapshots_path: /qdrant/snapshots
  
service:
  # 增加 HTTP 超时
  http_port: 6333
  grpc_port: 6334
  max_request_size_mb: 32
  
# 集合优化配置
hnsw_config:
  m: 16                    # 连接数，影响精度和内存
  ef_construct: 100        # 构建时搜索范围
  full_scan_threshold: 10000  # 全扫描阈值
```

### 缓存策略

#### Redis 配置

```bash
# redis.conf 优化
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### 应用层缓存

```python
# 启用各种缓存
ENABLE_EMBEDDING_CACHE=true
ENABLE_LLM_CACHE=true
ENABLE_RETRIEVAL_CACHE=true

# 缓存过期时间
EMBEDDING_CACHE_TTL=3600    # 1小时
LLM_CACHE_TTL=1800          # 30分钟
RETRIEVAL_CACHE_TTL=300     # 5分钟
```

## 监控与告警

### Prometheus 集成

#### 指标收集

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rag-pipeline'
    static_configs:
      - targets: ['api.your-domain.com:8020']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

#### 关键指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | 请求延迟分布 |
| `database_connections_active` | Gauge | 活跃数据库连接数 |
| `llm_calls_total` | Counter | LLM 调用总数 |
| `embedding_calls_total` | Counter | Embedding 调用总数 |
| `retrieval_operations_total` | Counter | 检索操作总数 |

### 告警规则

```yaml
# alerting_rules.yml
groups:
- name: rag-pipeline
  rules:
  - alert: ServiceDown
    expr: up{job="rag-pipeline"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "RAG Pipeline service is down"
      
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      
  - alert: HighLatency
    expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected"
      
  - alert: DatabaseConnectionsHigh
    expr: database_connections_active > 18
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Database connections near limit"
```

### 日志聚合

#### ELK Stack 配置

```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
  - add_docker_metadata:
      host: "unix:///var/run/docker.sock"

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "rag-pipeline-%{+yyyy.MM.dd}"
```

#### 日志格式

应用输出结构化 JSON 日志：

```json
{
  "timestamp": "2024-12-04T03:00:00.000Z",
  "level": "INFO",
  "logger": "app.services.query",
  "message": "[RETRIEVAL] hybrid 检索完成: 5 结果",
  "request_id": "abc123",
  "tenant_id": "tenant_001",
  "duration_ms": 245,
  "retriever": "hybrid",
  "top_k": 5,
  "result_count": 5
}
```

## 备份与恢复

### 数据库备份

#### 自动备份脚本

```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/opt/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kb_backup_$DATE.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
docker compose exec -T db pg_dump -U kb -d kb > $BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_FILE

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### 定时备份

```bash
# 添加到 crontab
0 2 * * * /opt/self-rag-pipeline/scripts/backup-db.sh
```

#### 恢复数据库

```bash
# 停止服务
docker compose stop api

# 恢复数据库
gunzip -c kb_backup_20241204_020000.sql.gz | \
  docker compose exec -T db psql -U kb -d kb

# 重启服务
docker compose start api
```

### 向量库备份

#### Qdrant 快照

```bash
# 创建快照
curl -X POST "http://localhost:6333/collections/{collection_name}/snapshots"

# 下载快照
curl -X GET "http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name}" \
  --output snapshot.tar

# 恢复快照
curl -X PUT "http://localhost:6333/collections/{collection_name}/snapshots/upload" \
  --form file=@snapshot.tar
```

#### 文件系统备份

```bash
# 停止 Qdrant 服务
docker compose stop qdrant

# 备份数据目录
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz \
  -C /var/lib/docker/volumes/self-rag-pipeline_qdrant_data/_data .

# 重启服务
docker compose start qdrant
```

## 故障排查

### 常见问题

#### 1. 数据库连接失败

**症状**：
```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionDoesNotExistError)
```

**排查步骤**：
```bash
# 检查数据库服务状态
docker compose ps db

# 检查数据库日志
docker compose logs db

# 测试连接
docker compose exec db psql -U kb -d kb -c "SELECT 1;"

# 检查网络连通性
docker compose exec api ping db
```

**解决方案**：
- 确认 PostgreSQL 服务运行正常
- 检查 DATABASE_URL 配置
- 验证网络连通性
- 检查防火墙设置

#### 2. 向量库连接超时

**症状**：
```
qdrant_client.http.exceptions.UnexpectedResponse: status_code=503
```

**排查步骤**：
```bash
# 检查 Qdrant 服务状态
docker compose ps qdrant

# 检查 Qdrant 健康状态
curl http://localhost:6333/health

# 检查 Qdrant 日志
docker compose logs qdrant

# 测试连接
curl http://localhost:6333/collections
```

**解决方案**：
- 确认 Qdrant 服务运行正常
- 检查 QDRANT_URL 配置
- 增加连接超时时间
- 检查磁盘空间

#### 3. LLM 调用超时

**症状**：
```
openai.APITimeoutError: Request timed out
```

**排查步骤**：
```bash
# 检查网络连通性
curl -I https://api.openai.com

# 测试 API Key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# 检查本地 Ollama 服务
curl http://localhost:11434/api/tags
```

**解决方案**：
- 检查 API Key 有效性
- 增加超时时间配置
- 检查网络代理设置
- 验证模型可用性

#### 4. 内存不足

**症状**：
```
docker: Error response from daemon: OOMKilled
```

**排查步骤**：
```bash
# 检查容器资源使用
docker stats

# 检查系统内存
free -h

# 检查 Docker 日志
docker compose logs api
```

**解决方案**：
- 增加容器内存限制
- 优化数据库连接池配置
- 减少并发 worker 数量
- 启用 swap 分区

### 性能问题诊断

#### 慢查询分析

```sql
-- 启用慢查询日志
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- 查看慢查询
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

#### 应用性能分析

```python
# 启用性能分析
import cProfile
import pstats

# 在关键路径添加性能监控
@profile_async
async def retrieve_chunks(...):
    # 检索逻辑
    pass
```

### 日志分析

#### 关键日志模式

```bash
# 错误日志
grep "ERROR" /var/log/rag-pipeline/app.log

# 慢请求
grep "duration_ms.*[5-9][0-9][0-9][0-9]" /var/log/rag-pipeline/app.log

# 认证失败
grep "INVALID_API_KEY\|UNAUTHORIZED" /var/log/rag-pipeline/app.log

# 数据库错误
grep "sqlalchemy\|asyncpg" /var/log/rag-pipeline/app.log
```

## 安全加固

### 网络安全

#### 防火墙配置

```bash
# 仅开放必要端口
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 8020/tcp   # 直接访问 API（通过代理）
ufw deny 5432/tcp   # PostgreSQL
ufw deny 6333/tcp   # Qdrant
ufw enable
```

#### SSL/TLS 配置

```nginx
# 强化 SSL 配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 访问控制

#### IP 白名单

```nginx
# 限制管理接口访问
location /admin {
    allow 192.168.1.0/24;  # 内网
    allow 10.0.0.0/8;      # VPN
    deny all;
    
    proxy_pass http://api_backend;
}
```

#### 速率限制

```nginx
# Nginx 速率限制
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    server {
        location /v1 {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api_backend;
        }
    }
}
```

### 容器安全

#### 非 root 用户

```dockerfile
# Dockerfile 安全配置
FROM python:3.11-slim

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录权限
WORKDIR /app
COPY --chown=appuser:appuser . .

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8020

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
```

#### 资源限制

```yaml
# docker-compose.yml 资源限制
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

## 升级与维护

### 滚动升级

#### Docker Compose 升级

```bash
# 1. 拉取新镜像
docker compose pull

# 2. 逐个重启服务
docker compose up -d --no-deps api

# 3. 验证服务健康
curl http://localhost:8020/health

# 4. 运行数据库迁移（如需要）
docker compose exec api alembic upgrade head
```

#### Kubernetes 滚动升级

```bash
# 更新镜像版本
kubectl set image deployment/rag-pipeline-api \
  api=your-registry/self_rag_pipeline-api:v1.1.0 \
  -n self-rag-pipeline

# 监控升级进度
kubectl rollout status deployment/rag-pipeline-api -n self-rag-pipeline

# 回滚（如需要）
kubectl rollout undo deployment/rag-pipeline-api -n self-rag-pipeline
```

### 数据库迁移

#### 迁移流程

```bash
# 1. 备份数据库
./scripts/backup-db.sh

# 2. 检查迁移脚本
docker compose exec api alembic history
docker compose exec api alembic show head

# 3. 执行迁移
docker compose exec api alembic upgrade head

# 4. 验证迁移结果
docker compose exec api python -c "
from app.db.session import async_session_maker
import asyncio
async def test():
    async with async_session_maker() as session:
        result = await session.execute('SELECT version_num FROM alembic_version')
        print('Current version:', result.scalar())
asyncio.run(test())
"
```

### 定期维护任务

#### 清理任务

```bash
#!/bin/bash
# maintenance.sh

# 清理过期审计日志（保留90天）
docker compose exec api python -c "
from app.services.audit import cleanup_old_audit_logs
import asyncio
asyncio.run(cleanup_old_audit_logs(days=90))
"

# 清理 Docker 镜像和容器
docker system prune -f

# 清理日志文件
find /var/log -name "*.log" -mtime +30 -delete

# 数据库维护
docker compose exec db psql -U kb -d kb -c "VACUUM ANALYZE;"
```

#### 定时任务

```bash
# 添加到 crontab
0 2 * * * /opt/self-rag-pipeline/scripts/backup-db.sh
0 3 * * 0 /opt/self-rag-pipeline/scripts/maintenance.sh
```

---

如有问题，请参考故障排查章节或联系运维团队。