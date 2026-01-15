# 生产环境部署指南

**版本**: 1.0  
**日期**: 2026-01-15  
**目标**: Self-RAG Pipeline 生产环境部署清单

---

## 📋 部署前检查清单

### 1. 环境配置 ✅

#### 1.1 基础环境
- [ ] 服务器配置检查（CPU、内存、磁盘）
- [ ] 操作系统更新到最新稳定版
- [ ] Docker 和 Docker Compose 安装
- [ ] 防火墙配置（开放必要端口）
- [ ] SSL/TLS 证书准备（HTTPS）

**推荐配置**:
```
最低配置:
- CPU: 4 核
- 内存: 16 GB
- 磁盘: 100 GB SSD

推荐配置:
- CPU: 8 核+
- 内存: 32 GB+
- 磁盘: 500 GB SSD+
```

#### 1.2 依赖服务
- [ ] PostgreSQL 15+ 部署（或使用云服务）
- [ ] Redis 6+ 部署（缓存和限流）
- [ ] Qdrant 向量数据库部署
- [ ] 反向代理配置（Nginx/Caddy）
- [ ] 对象存储配置（可选，存储大文件）

---

### 2. 安全配置 🔒

#### 2.1 密钥和令牌

**必须修改的密钥**:
```bash
# .env 文件中必须修改这些配置

# 1. Admin Token（使用 API 创建哈希令牌）
ADMIN_TOKEN=<使用 Admin Token API 生成的安全令牌>

# 2. 数据库密码
DATABASE_URL=postgresql+asyncpg://kb:<强密码>@db:5432/kb

# 3. Redis 密码（如果启用）
REDIS_URL=redis://:<强密码>@redis:6379/0

# 4. Qdrant API Key（如果启用）
QDRANT_API_KEY=<生成的安全密钥>

# 5. 模型提供商 API Keys
QWEN_API_KEY=<您的真实 API Key>
OPENAI_API_KEY=<您的真实 API Key>
GEMINI_API_KEY=<您的真实 API Key>
```

**生成 Admin Token**:
```bash
# 1. 启动服务后，使用临时 token 创建正式的 Admin Token
curl -X POST http://localhost:8020/admin/tokens \
  -H "X-Admin-Token: temporary_token_for_first_time" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Admin Token",
    "description": "生产环境管理员令牌",
    "expires_at": null
  }'

# 2. 记录返回的 token（只显示一次！）
# 3. 更新 .env 文件中的 ADMIN_TOKEN
# 4. 撤销临时 token
```

#### 2.2 CORS 配置

**修改 `app/main.py`**:
```python
# ❌ 开发环境（允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 不安全！
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 生产环境（限制来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",
        "https://app.your-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)
```

#### 2.3 API 限流

```bash
# .env
API_RATE_LIMIT_PER_MINUTE=600  # 生产环境可能需要降低
API_RATE_LIMIT_WINDOW_SECONDS=60

# 启用 Redis 限流（推荐）
REDIS_URL=redis://<password>@redis:6379/0
```

#### 2.4 数据库连接池

```bash
# .env
# PostgreSQL 连接池配置
DB_POOL_SIZE=20              # 连接池大小
DB_MAX_OVERFLOW=10           # 最大溢出连接数
DB_POOL_TIMEOUT=30           # 连接超时（秒）
DB_POOL_RECYCLE=3600         # 连接回收时间（秒）
```

---

### 3. 数据库准备 💾

#### 3.1 数据库迁移

```bash
# 1. 备份现有数据库（如果有）
pg_dump -h <host> -U kb kb > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 运行迁移
DATABASE_URL=postgresql+asyncpg://kb:<password>@<host>:5432/kb \
uv run alembic upgrade head

# 3. 验证迁移
uv run alembic current
uv run alembic history
```

#### 3.2 数据库索引优化

```sql
-- 检查索引是否存在
\d+ tenants
\d+ knowledge_bases
\d+ documents
\d+ chunks

-- 添加生产环境推荐索引（如果缺失）
CREATE INDEX CONCURRENTLY idx_chunks_tenant_kb 
ON chunks(tenant_id, knowledge_base_id);

CREATE INDEX CONCURRENTLY idx_documents_tenant_kb 
ON documents(tenant_id, knowledge_base_id);

CREATE INDEX CONCURRENTLY idx_chunks_embedding_status 
ON chunks(indexing_status) WHERE indexing_status != 'indexed';
```

#### 3.3 数据库维护计划

```sql
-- 设置自动 VACUUM
ALTER TABLE chunks SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE documents SET (autovacuum_vacuum_scale_factor = 0.1);

-- 定期维护脚本（cron 任务）
-- 每天凌晨 3 点执行
-- 0 3 * * * psql -U kb -d kb -c "VACUUM ANALYZE;"
```

---

### 4. 向量数据库配置 🔍

#### 4.1 Qdrant 持久化

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:v1.9.0
    volumes:
      - ./qdrant_data:/qdrant/storage  # 持久化存储
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}  # 启用认证
    restart: always
```

#### 4.2 向量库备份

```bash
# Qdrant 备份脚本
#!/bin/bash
BACKUP_DIR="/backup/qdrant/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 创建快照
curl -X POST "http://localhost:6333/collections/kb_shared/snapshots" \
  -H "api-key: $QDRANT_API_KEY"

# 下载快照
curl "http://localhost:6333/collections/kb_shared/snapshots/<snapshot_name>" \
  -H "api-key: $QDRANT_API_KEY" \
  -o "$BACKUP_DIR/kb_shared.snapshot"
```

---

### 5. Redis 配置 ⚡

#### 5.1 Redis 持久化

```bash
# redis.conf
appendonly yes
appendfilename "appendonly.aof"
save 900 1      # 900秒内至少1个key变化就保存
save 300 10     # 300秒内至少10个key变化就保存
save 60 10000   # 60秒内至少10000个key变化就保存

# 内存策略
maxmemory 2gb
maxmemory-policy allkeys-lru
```

#### 5.2 Redis 监控

```bash
# 启用 Redis 监控
redis-cli INFO stats
redis-cli INFO memory
redis-cli SLOWLOG GET 10
```

---

### 6. 日志和监控 📊

#### 6.1 日志配置

```bash
# .env
LOG_LEVEL=INFO              # 生产环境使用 INFO（不要用 DEBUG）
TIMEZONE=Asia/Shanghai

# 日志轮转配置（使用 logrotate）
cat > /etc/logrotate.d/rag-pipeline << 'EOF'
/var/log/rag-pipeline/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        docker-compose restart api
    endscript
}
EOF
```

#### 6.2 结构化日志

确保所有日志都是 JSON 格式，便于日志聚合和分析：

```python
# app/infra/logging.py 已配置为 JSON 格式
# 确保生产环境使用正确的日志级别
```

#### 6.3 监控指标

**必须监控的指标**:
1. API 响应时间（P50, P95, P99）
2. 错误率（4xx, 5xx）
3. 数据库连接池使用率
4. Redis 缓存命中率
5. 磁盘使用率
6. 内存使用率
7. CPU 使用率

**推荐工具**:
- Prometheus + Grafana
- ELK Stack（Elasticsearch + Logstash + Kibana）
- 云平台监控（AWS CloudWatch, 阿里云监控等）

---

### 7. 反向代理配置 🌐

#### 7.1 Nginx 配置示例

```nginx
# /etc/nginx/sites-available/rag-pipeline

upstream rag_api {
    least_conn;
    server localhost:8020 max_fails=3 fail_timeout=30s;
    # 如果有多个实例
    # server localhost:8021 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 请求体大小限制（上传文档）
    client_max_body_size 100M;

    # 超时配置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://rag_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 健康检查端点（不需要认证）
    location /health {
        proxy_pass http://rag_api/health;
        access_log off;
    }

    # 访问日志
    access_log /var/log/nginx/rag-pipeline-access.log;
    error_log /var/log/nginx/rag-pipeline-error.log;
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name api.your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

#### 7.2 Caddy 配置示例（更简单）

```caddyfile
# Caddyfile

api.your-domain.com {
    reverse_proxy localhost:8020
    
    # 自动 HTTPS
    tls your-email@example.com
    
    # 安全头
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        X-XSS-Protection "1; mode=block"
    }
    
    # 请求体大小限制
    request_body {
        max_size 100MB
    }
}
```

---

### 8. Docker 生产配置 🐳

#### 8.1 优化 docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kb
      POSTGRES_USER: kb
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # 从环境变量读取
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kb"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.9.0
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
      network: host  # 加速构建
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    env_file:
      - .env
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    depends_on:
      - api
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  qdrant_data:
    driver: local

networks:
  default:
    name: rag_pipeline_network
```

#### 8.2 优化 Dockerfile

```dockerfile
# 多阶段构建，减小镜像体积
FROM python:3.11-slim as builder

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖到虚拟环境
RUN uv sync --no-dev

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 复制依赖
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# 启动脚本
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
```

---

### 9. 备份策略 💾

#### 9.1 自动备份脚本

```bash
#!/bin/bash
# /opt/backup/rag-pipeline-backup.sh

set -e

BACKUP_DIR="/backup/rag-pipeline"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR/{postgres,qdrant,config}

# 1. PostgreSQL 备份
echo "备份 PostgreSQL..."
docker exec rag_kb_postgres pg_dump -U kb kb | gzip > \
    $BACKUP_DIR/postgres/kb_${DATE}.sql.gz

# 2. Qdrant 备份
echo "备份 Qdrant..."
tar -czf $BACKUP_DIR/qdrant/qdrant_${DATE}.tar.gz \
    ./qdrant_data/

# 3. 配置文件备份
echo "备份配置..."
cp .env $BACKUP_DIR/config/.env_${DATE}
cp docker-compose.yml $BACKUP_DIR/config/docker-compose_${DATE}.yml

# 4. 删除旧备份
echo "清理旧备份..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

# 5. 上传到对象存储（可选）
# aws s3 sync $BACKUP_DIR s3://your-backup-bucket/rag-pipeline/

echo "备份完成: $DATE"
```

#### 9.2 定时任务

```bash
# crontab -e
# 每天凌晨 2 点备份
0 2 * * * /opt/backup/rag-pipeline-backup.sh >> /var/log/backup.log 2>&1
```

---

### 10. 性能优化 ⚡

#### 10.1 Redis 缓存配置

```bash
# .env
REDIS_CACHE_ENABLED=true
REDIS_CACHE_TTL=300           # 查询缓存 5 分钟
REDIS_CONFIG_CACHE_TTL=600    # 配置缓存 10 分钟
```

#### 10.2 BM25 限制

```bash
# .env
BM25_MAX_RECORDS_PER_KB=10000
BM25_MAX_TOTAL_RECORDS=100000
```

#### 10.3 连接池优化

```python
# app/db/session.py
engine = create_async_engine(
    settings.database_url,
    pool_size=20,              # 生产环境增加池大小
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,        # 检查连接有效性
)
```

---

### 11. 健康检查和恢复 🏥

#### 11.1 健康检查端点

确保 `/health` 端点返回详细信息：

```python
# app/api/routes/health.py
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": await check_db(),
            "redis": await check_redis(),
            "qdrant": await check_qdrant(),
        }
    }
```

#### 11.2 监控脚本

```bash
#!/bin/bash
# /opt/monitor/check-health.sh

API_URL="http://localhost:8020/health"
ALERT_EMAIL="admin@example.com"

response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $response -ne 200 ]; then
    echo "API 健康检查失败! HTTP $response" | \
        mail -s "RAG Pipeline Alert" $ALERT_EMAIL
    
    # 尝试重启服务
    docker-compose restart api
fi
```

---

### 12. 安全加固 🔐

#### 12.1 防火墙规则

```bash
# UFW 示例
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw enable
```

#### 12.2 SSH 加固

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Port 2222  # 修改默认端口
```

#### 12.3 敏感文件权限

```bash
chmod 600 .env
chmod 600 alembic.ini
chown appuser:appuser .env
```

---

### 13. 部署检查清单 ✅

#### 启动前检查
- [ ] 所有密钥已修改（Admin Token, DB 密码, Redis 密码等）
- [ ] CORS 已限制到具体域名
- [ ] SSL 证书已配置
- [ ] 数据库迁移已完成
- [ ] 备份脚本已配置
- [ ] 监控已启用
- [ ] 日志轮转已配置
- [ ] 防火墙规则已设置
- [ ] 健康检查已测试

#### 启动后检查
- [ ] 所有服务容器运行正常
- [ ] 数据库连接正常
- [ ] Redis 缓存正常
- [ ] Qdrant 向量库正常
- [ ] API 健康检查返回 200
- [ ] 前端可以访问
- [ ] 日志正常输出
- [ ] 创建测试租户成功
- [ ] 创建测试知识库成功
- [ ] 上传测试文档成功
- [ ] 检索测试成功
- [ ] RAG 生成测试成功

---

### 14. 运维文档 📚

#### 14.1 常见问题排查

**数据库连接失败**:
```bash
# 检查数据库状态
docker-compose ps db
docker logs rag_kb_postgres

# 测试连接
psql -h localhost -p 5435 -U kb -d kb
```

**Redis 连接失败**:
```bash
# 检查 Redis 状态
docker-compose ps redis
docker logs rag_kb_redis

# 测试连接
redis-cli -h localhost -p 6379 -a <password> PING
```

**向量库同步问题**:
```bash
# 检查 Qdrant 状态
curl http://localhost:6333/collections

# 查看 collection 信息
curl http://localhost:6333/collections/kb_shared
```

#### 14.2 紧急回滚

```bash
# 1. 停止服务
docker-compose down

# 2. 恢复数据库
gunzip -c /backup/postgres/kb_<date>.sql.gz | \
    docker exec -i rag_kb_postgres psql -U kb kb

# 3. 恢复 Qdrant
tar -xzf /backup/qdrant/qdrant_<date>.tar.gz -C ./

# 4. 恢复配置
cp /backup/config/.env_<date> .env

# 5. 重启服务
docker-compose up -d
```

---

### 15. 扩展性规划 📈

#### 15.1 水平扩展

**API 多实例部署**:
```yaml
# docker-compose.yml
services:
  api1:
    <<: *api-common
    ports:
      - "8020:8020"
  
  api2:
    <<: *api-common
    ports:
      - "8021:8020"
  
  api3:
    <<: *api-common
    ports:
      - "8022:8020"
```

**Nginx 负载均衡**:
```nginx
upstream rag_api {
    least_conn;
    server localhost:8020;
    server localhost:8021;
    server localhost:8022;
}
```

#### 15.2 读写分离

PostgreSQL 主从复制配置（可选）。

---

## 🚀 快速部署脚本

```bash
#!/bin/bash
# deploy.sh - 一键部署脚本

set -e

echo "🚀 开始部署 RAG Pipeline..."

# 1. 检查依赖
echo "检查依赖..."
command -v docker >/dev/null 2>&1 || { echo "需要安装 Docker"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "需要安装 Docker Compose"; exit 1; }

# 2. 备份现有数据（如果存在）
if [ -f .env ]; then
    echo "备份现有配置..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# 3. 配置环境变量
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件，修改所有密钥和配置"
    exit 1
fi

# 4. 拉取最新镜像
echo "拉取 Docker 镜像..."
docker-compose pull

# 5. 构建应用
echo "构建应用..."
docker-compose build --no-cache

# 6. 启动服务
echo "启动服务..."
docker-compose up -d

# 7. 等待服务就绪
echo "等待服务启动..."
sleep 30

# 8. 运行数据库迁移
echo "运行数据库迁移..."
docker-compose exec api uv run alembic upgrade head

# 9. 健康检查
echo "健康检查..."
curl -f http://localhost:8020/health || { echo "健康检查失败"; exit 1; }

echo "✅ 部署完成！"
echo "API: http://localhost:8020"
echo "Frontend: http://localhost:3003"
echo ""
echo "下一步:"
echo "1. 创建 Admin Token"
echo "2. 配置 Nginx 反向代理"
echo "3. 配置 SSL 证书"
echo "4. 设置定时备份"
```

---

## 📞 支持和联系

如有问题，请参考：
- 项目文档: `/docs`
- 健康检查: `http://your-domain.com/health`
- 日志位置: `/var/log/rag-pipeline/`

---

**最后更新**: 2026-01-15
