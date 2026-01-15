# 运维部署

本节为系统管理员和运维工程师提供 Self-RAG Pipeline 的部署、配置、监控和维护指南。涵盖从开发环境到生产环境的完整运维流程。

## 概述

Self-RAG Pipeline 采用云原生架构设计，支持多种部署方式：

- **Docker Compose**：适合开发和小规模部署
- **Kubernetes**：适合生产环境和大规模部署
- **云服务**：支持主流云平台部署

## 部署架构

### 组件依赖关系

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   负载均衡器    │    │   API 服务集群  │    │   前端服务      │
│   (Nginx/ALB)   │────│   (FastAPI)     │    │   (Next.js)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Qdrant      │    │     Redis       │
│   (主数据库)    │    │   (向量数据库)  │    │    (缓存)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                    ┌─────────────────┐
                    │   外部 LLM 服务 │
                    │ (OpenAI/Ollama) │
                    └─────────────────┘
```

### 资源需求

#### 最小配置（开发/测试）
- **CPU**：2 核心
- **内存**：4GB RAM
- **存储**：20GB SSD
- **网络**：1Gbps

#### 推荐配置（生产环境）
- **CPU**：8+ 核心
- **内存**：16GB+ RAM
- **存储**：100GB+ SSD
- **网络**：10Gbps
- **高可用**：多节点部署

#### 大规模部署
- **API 服务**：多实例负载均衡
- **数据库**：主从复制 + 读写分离
- **向量数据库**：集群部署
- **缓存**：Redis 集群

## 快速部署

### Docker Compose 部署

适合开发环境和小规模生产部署：

```bash
# 1. 克隆项目
git clone https://github.com/your-org/self-rag-pipeline.git
cd self-rag-pipeline

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置必要参数

# 3. 启动所有服务
docker-compose up -d

# 4. 运行数据库迁移
docker-compose exec api uv run alembic upgrade head

# 5. 验证部署
curl http://localhost:8020/health
```

### 生产环境部署

#### 1. 环境准备

```bash
# 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. 配置文件

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: self-rag-pipeline:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - QDRANT_URL=${QDRANT_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - qdrant
      - redis
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - app-network

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - app-network

  qdrant:
    image: qdrant/qdrant:v1.7.0
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - app-network

volumes:
  postgres_data:
  qdrant_data:
  redis_data:

networks:
  app-network:
    driver: bridge
```

#### 3. Nginx 配置

```nginx
# nginx.conf
upstream api_backend {
    server api:8020;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # API 代理
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
}
```

## 配置管理

### 环境变量配置

#### 核心配置
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/kb
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379

# LLM 配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434

# Embedding 配置
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024

# 安全配置
SECRET_KEY=your-secret-key-here
ADMIN_TOKEN=your-admin-token-here
```

#### 高级配置
```bash
# 性能配置
MAX_WORKERS=4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# 限流配置
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_BURST=10

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 向量存储隔离策略
QDRANT_ISOLATION_STRATEGY=partition  # partition/collection/auto
```

### 配置验证

```bash
# 验证配置
docker-compose exec api python -c "
from app.config import settings
print('Database URL:', settings.DATABASE_URL)
print('Qdrant URL:', settings.QDRANT_URL)
print('LLM Provider:', settings.LLM_PROVIDER)
"
```

## 监控和日志

### 应用监控

#### 健康检查端点
```bash
# 基础健康检查
curl http://localhost:8020/health

# 详细健康检查
curl http://localhost:8020/health/detailed
```

#### 指标收集
```python
# 自定义指标
from app.infra.metrics import metrics

# API 调用计数
metrics.increment('api.requests', tags={'endpoint': '/v1/retrieve'})

# 响应时间
with metrics.timer('api.response_time'):
    # 处理请求
    pass
```

### 日志管理

#### 结构化日志
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.api.routes.retrieve",
  "message": "Retrieve request completed",
  "request_id": "req_123456",
  "tenant_id": "tenant_abc",
  "duration_ms": 150,
  "results_count": 5
}
```

#### 日志收集
```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
        labels: "service=api"

  fluentd:
    image: fluent/fluentd:v1.16
    volumes:
      - ./fluentd.conf:/fluentd/etc/fluent.conf
      - /var/log:/var/log
    ports:
      - "24224:24224"
```

### 性能监控

#### 数据库监控
```sql
-- 慢查询监控
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
WHERE mean_exec_time > 1000 
ORDER BY mean_exec_time DESC;

-- 连接数监控
SELECT count(*) as connections, state 
FROM pg_stat_activity 
GROUP BY state;
```

#### 向量数据库监控
```bash
# Qdrant 集群状态
curl http://localhost:6333/cluster

# 集合信息
curl http://localhost:6333/collections

# 内存使用
curl http://localhost:6333/metrics
```

## 备份和恢复

### 数据库备份

#### PostgreSQL 备份
```bash
# 创建备份
docker-compose exec db pg_dump -U postgres kb > backup_$(date +%Y%m%d_%H%M%S).sql

# 定时备份脚本
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec db pg_dump -U postgres kb | gzip > $BACKUP_DIR/kb_$DATE.sql.gz

# 清理旧备份（保留 30 天）
find $BACKUP_DIR -name "kb_*.sql.gz" -mtime +30 -delete
```

#### Qdrant 备份
```bash
# 创建快照
curl -X POST http://localhost:6333/collections/{collection_name}/snapshots

# 下载快照
curl http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name} -o snapshot.tar
```

### 恢复流程

#### 数据库恢复
```bash
# 停止服务
docker-compose stop api

# 恢复数据库
docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS kb;"
docker-compose exec db psql -U postgres -c "CREATE DATABASE kb;"
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U postgres kb

# 启动服务
docker-compose start api
```

#### 向量数据恢复
```bash
# 上传快照
curl -X PUT http://localhost:6333/collections/{collection_name}/snapshots/upload \
  -H "Content-Type: application/octet-stream" \
  --data-binary @snapshot.tar

# 恢复快照
curl -X PUT http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name}/recover
```

## 安全配置

### SSL/TLS 配置

#### 证书生成
```bash
# 自签名证书（开发环境）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem

# Let's Encrypt 证书（生产环境）
certbot certonly --webroot -w /var/www/html -d your-domain.com
```

#### HTTPS 强制
```nginx
# 强制 HTTPS 重定向
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 防火墙配置

```bash
# UFW 防火墙规则
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # PostgreSQL (仅内网)
sudo ufw deny 6333/tcp   # Qdrant (仅内网)
sudo ufw enable
```

### API 安全

#### 限流配置
```python
# 自定义限流规则
RATE_LIMITS = {
    "default": "120/minute",
    "admin": "1000/minute",
    "read": "60/minute"
}
```

#### API Key 管理
```bash
# 创建 API Key
curl -X POST http://localhost:8020/admin/tenants/{tenant_id}/api-keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "write", "name": "production-key"}'

# 轮换 API Key
curl -X POST http://localhost:8020/admin/api-keys/{key_id}/rotate \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

## 故障排查

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库状态
docker-compose ps db
docker-compose logs db

# 测试连接
docker-compose exec api python -c "
from app.db.session import get_db_session
import asyncio
async def test():
    async with get_db_session() as db:
        print('Database connection OK')
asyncio.run(test())
"
```

#### 2. 向量数据库问题
```bash
# 检查 Qdrant 状态
curl http://localhost:6333/health
curl http://localhost:6333/collections

# 重建索引
curl -X DELETE http://localhost:6333/collections/{collection_name}
# 重新上传文档
```

#### 3. LLM 服务问题
```bash
# 测试 LLM 连接
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:14b", "prompt": "Hello"}'
```

### 性能调优

#### 数据库优化
```sql
-- 创建索引
CREATE INDEX CONCURRENTLY idx_chunks_tenant_kb 
ON chunks(tenant_id, knowledge_base_id);

-- 分析查询计划
EXPLAIN ANALYZE SELECT * FROM chunks 
WHERE tenant_id = 'xxx' AND knowledge_base_id = 'yyy';
```

#### 应用优化
```python
# 连接池配置
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30

# 异步批处理
async def batch_embed(texts: List[str], batch_size: int = 32):
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = await embed_texts(batch)
        yield embeddings
```

## 扩展部署

### Kubernetes 部署

#### 部署清单
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: self-rag-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: self-rag-api
  template:
    metadata:
      labels:
        app: self-rag-api
    spec:
      containers:
      - name: api
        image: self-rag-pipeline:latest
        ports:
        - containerPort: 8020
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

#### 服务配置
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: self-rag-api-service
spec:
  selector:
    app: self-rag-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8020
  type: LoadBalancer
```

### 云平台部署

#### AWS 部署
- **ECS Fargate**：容器化部署
- **RDS PostgreSQL**：托管数据库
- **ElastiCache Redis**：托管缓存
- **ALB**：负载均衡

#### 阿里云部署
- **容器服务 ACK**：Kubernetes 集群
- **RDS**：云数据库
- **Redis**：云缓存
- **SLB**：负载均衡

## 运维指南

### 日常维护

#### 1. 系统监控检查
```bash
# 每日检查脚本
#!/bin/bash
echo "=== 系统状态检查 $(date) ==="

# 服务状态
docker-compose ps

# 磁盘使用
df -h

# 内存使用
free -h

# 数据库连接数
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# API 健康检查
curl -s http://localhost:8020/health | jq .
```

#### 2. 日志轮转
```bash
# logrotate 配置
/var/log/self-rag/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker-compose restart api
    endscript
}
```

#### 3. 定期清理
```bash
# 清理脚本
#!/bin/bash

# 清理 Docker 镜像
docker system prune -f

# 清理旧日志
find /var/log/self-rag -name "*.log.*" -mtime +30 -delete

# 清理临时文件
find /tmp -name "self-rag-*" -mtime +1 -delete
```

### 升级流程

#### 1. 准备阶段
```bash
# 备份数据
./backup.sh

# 拉取新镜像
docker-compose pull
```

#### 2. 升级执行
```bash
# 滚动升级
docker-compose up -d --no-deps api

# 运行迁移
docker-compose exec api uv run alembic upgrade head

# 验证升级
curl http://localhost:8020/health
```

#### 3. 回滚流程
```bash
# 如果升级失败，回滚到之前版本
docker-compose down
docker-compose up -d --force-recreate

# 恢复数据库（如需要）
./restore.sh backup_20240115_103000.sql.gz
```

## 下一步

深入了解各个运维主题：

- **[部署指南](./deployment)** - 详细的部署步骤和配置
- **[安全指南](./security)** - 安全配置和最佳实践
- **[监控指南](./monitoring)** - 监控系统搭建和配置
- **[问题排查](./troubleshooting)** - 常见问题和解决方案

---

需要帮助？查看 [问题排查指南](./troubleshooting) 或联系技术支持团队。