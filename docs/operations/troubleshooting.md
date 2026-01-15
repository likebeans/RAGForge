# 故障排查指南

本文档提供 Self-RAG Pipeline 系统常见问题的诊断和解决方案。

## 快速诊断

### 系统健康检查

```bash
# 1. 检查服务状态
curl http://localhost:8020/health
curl http://localhost:8020/ready

# 2. 检查容器状态
docker compose ps

# 3. 查看服务日志
docker compose logs -f api
docker compose logs -f db
docker compose logs -f qdrant
```

### 关键指标检查

```bash
# 检查系统指标
curl http://localhost:8020/metrics | jq

# 检查数据库连接
docker compose exec db psql -U kb -d kb -c "SELECT count(*) FROM pg_stat_activity;"

# 检查向量库状态
curl http://localhost:6333/collections | jq
```

## 服务启动问题

### 1. API 服务无法启动

#### 症状
```
docker compose up api
ERROR: Service 'api' failed to build
```

#### 可能原因与解决方案

**原因1：依赖服务未就绪**
```bash
# 检查依赖服务
docker compose ps db qdrant

# 等待依赖服务启动
docker compose up -d db qdrant
sleep 30
docker compose up api
```

**原因2：环境变量配置错误**
```bash
# 检查环境变量
docker compose config

# 验证必需的环境变量
echo $DATABASE_URL
echo $QDRANT_URL
echo $ADMIN_TOKEN
```

**原因3：端口冲突**
```bash
# 检查端口占用
netstat -tlnp | grep 8020
lsof -i :8020

# 修改端口或停止冲突进程
docker compose down
sudo kill -9 <PID>
docker compose up
```

### 2. 数据库连接失败

#### 症状
```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionDoesNotExistError)
could not connect to server: Connection refused
```

#### 诊断步骤

```bash
# 1. 检查 PostgreSQL 服务状态
docker compose ps db
docker compose logs db

# 2. 测试数据库连接
docker compose exec db psql -U kb -d kb -c "SELECT version();"

# 3. 检查网络连通性
docker compose exec api ping db

# 4. 验证连接字符串
echo $DATABASE_URL
```

#### 解决方案

**方案1：重启数据库服务**
```bash
docker compose restart db
# 等待服务完全启动
sleep 10
docker compose restart api
```

**方案2：检查数据库配置**
```bash
# 检查数据库初始化
docker compose exec db psql -U kb -d kb -c "\dt"

# 重新初始化（谨慎操作）
docker compose down
docker volume rm self-rag-pipeline_postgres_data
docker compose up -d db
# 等待初始化完成
docker compose exec api alembic upgrade head
```

**方案3：修复连接池配置**
```python
# app/db/session.py
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,  # 添加连接预检查
)
```

### 3. 向量库连接问题

#### 症状
```
qdrant_client.http.exceptions.UnexpectedResponse: status_code=503
Connection to Qdrant failed
```

#### 诊断步骤

```bash
# 1. 检查 Qdrant 服务状态
docker compose ps qdrant
curl http://localhost:6333/health

# 2. 检查 Qdrant 日志
docker compose logs qdrant

# 3. 测试 API 连接
curl http://localhost:6333/collections

# 4. 检查存储空间
df -h
docker system df
```

#### 解决方案

**方案1：重启 Qdrant 服务**
```bash
docker compose restart qdrant
# 等待服务启动
sleep 15
curl http://localhost:6333/health
```

**方案2：清理存储空间**
```bash
# 检查磁盘使用
du -sh /var/lib/docker/volumes/self-rag-pipeline_qdrant_data/

# 清理无用数据（谨慎操作）
docker compose stop qdrant
docker volume prune
docker compose up -d qdrant
```

**方案3：重建向量库**
```bash
# 备份重要数据
curl -X POST "http://localhost:6333/collections/kb_shared/snapshots"

# 删除并重建 collection
curl -X DELETE "http://localhost:6333/collections/kb_shared"

# 重新创建 collection（通过 API 上传文档会自动创建）
```

## 运行时问题

### 1. API 响应缓慢

#### 症状
- 请求超时
- 响应时间 > 30秒
- 前端显示加载中

#### 诊断步骤

```bash
# 1. 检查系统资源
top
htop
docker stats

# 2. 检查数据库性能
docker compose exec db psql -U kb -d kb -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"

# 3. 检查网络延迟
ping api.openai.com
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8020/health"

# 4. 分析应用日志
docker compose logs api | grep -E "(ERROR|WARN|duration_ms)"
```

#### 解决方案

**方案1：优化数据库查询**
```sql
-- 添加缺失的索引
CREATE INDEX CONCURRENTLY idx_chunks_tenant_kb ON chunks(tenant_id, knowledge_base_id);
CREATE INDEX CONCURRENTLY idx_documents_tenant ON documents(tenant_id);

-- 更新统计信息
ANALYZE;
```

**方案2：调整连接池配置**
```python
# 增加数据库连接池大小
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# 减少连接超时
DATABASE_POOL_TIMEOUT=10
```

**方案3：启用缓存**
```bash
# 启用 Redis 缓存
REDIS_URL=redis://redis:6379/0
ENABLE_EMBEDDING_CACHE=true
ENABLE_LLM_CACHE=true
EMBEDDING_CACHE_TTL=3600
```

**方案4：增加资源配置**
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
```

### 2. 内存不足 (OOM)

#### 症状
```
docker: Error response from daemon: OOMKilled
Container was killed due to OOM
```

#### 诊断步骤

```bash
# 1. 检查内存使用
free -h
docker stats --no-stream

# 2. 检查容器内存限制
docker inspect <container_id> | grep -i memory

# 3. 分析内存泄漏
docker compose exec api python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# 4. 检查 swap 使用
swapon --show
```

#### 解决方案

**方案1：增加容器内存限制**
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 2G
```

**方案2：优化应用配置**
```bash
# 减少 worker 数量
UVICORN_WORKERS=2

# 减少数据库连接池
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=15

# 启用内存优化
PYTHONOPTIMIZE=1
```

**方案3：启用 swap**
```bash
# 创建 swap 文件
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. 高错误率

#### 症状
- 大量 5xx 错误
- API 调用失败
- 用户无法正常使用

#### 诊断步骤

```bash
# 1. 统计错误类型
docker compose logs api | grep ERROR | cut -d' ' -f4- | sort | uniq -c | sort -nr

# 2. 检查错误模式
docker compose logs api | grep -E "(500|502|503|504)" | tail -20

# 3. 分析错误原因
curl -v http://localhost:8020/v1/knowledge-bases \
  -H "Authorization: Bearer invalid-key"

# 4. 检查依赖服务
curl http://localhost:6333/health
docker compose exec db psql -U kb -d kb -c "SELECT 1;"
```

#### 解决方案

**方案1：修复认证问题**
```bash
# 检查 API Key 配置
docker compose exec api python -c "
from app.auth.api_key import verify_api_key
import asyncio
async def test():
    # 测试 API Key 验证
    pass
"

# 重新生成管理员 Token
ADMIN_TOKEN=$(openssl rand -base64 32)
echo "New admin token: $ADMIN_TOKEN"
```

**方案2：修复数据库问题**
```bash
# 检查数据库连接
docker compose exec api python -c "
from app.db.session import async_session_maker
import asyncio
async def test():
    try:
        async with async_session_maker() as session:
            await session.execute('SELECT 1')
        print('Database OK')
    except Exception as e:
        print(f'Database Error: {e}')
asyncio.run(test())
"

# 重建连接池
docker compose restart api
```

**方案3：修复外部服务调用**
```bash
# 测试 OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# 测试本地 Ollama
curl http://localhost:11434/api/tags

# 检查网络代理
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

## 数据问题

### 1. 文档上传失败

#### 症状
```
{"detail": "Document ingestion failed", "code": "INGESTION_ERROR"}
```

#### 诊断步骤

```bash
# 1. 检查文档内容
curl -X POST http://localhost:8020/v1/knowledge-bases/{kb_id}/documents \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "test", "content": "test content"}' \
  -v

# 2. 检查切分器配置
docker compose exec api python -c "
from app.pipeline import operator_registry
chunker = operator_registry.get('chunker', 'recursive')
print('Chunker available:', chunker is not None)
"

# 3. 检查向量化服务
curl http://localhost:11434/api/embeddings \
  -d '{"model": "bge-m3", "prompt": "test"}'
```

#### 解决方案

**方案1：修复切分器问题**
```python
# 检查切分器注册
from app.pipeline.registry import operator_registry
print("Available chunkers:", operator_registry.list_operators("chunker"))

# 重新注册切分器
from app.pipeline.chunkers import *  # 重新导入所有切分器
```

**方案2：修复向量化问题**
```bash
# 检查 Embedding 配置
echo $EMBEDDING_PROVIDER
echo $EMBEDDING_MODEL

# 测试 Embedding 服务
docker compose exec api python -c "
from app.infra.embeddings import get_embedding
import asyncio
async def test():
    try:
        result = await get_embedding('test')
        print(f'Embedding OK: {len(result)} dimensions')
    except Exception as e:
        print(f'Embedding Error: {e}')
asyncio.run(test())
"
```

**方案3：检查权限问题**
```bash
# 验证 API Key 权限
curl -X GET http://localhost:8020/v1/api-keys \
  -H "Authorization: Bearer $API_KEY"

# 检查知识库权限
curl -X GET http://localhost:8020/v1/knowledge-bases/{kb_id} \
  -H "Authorization: Bearer $API_KEY"
```

### 2. 检索结果为空

#### 症状
```json
{"results": [], "total": 0}
```

#### 诊断步骤

```bash
# 1. 检查知识库中是否有数据
curl -X GET http://localhost:8020/v1/knowledge-bases/{kb_id}/documents \
  -H "Authorization: Bearer $API_KEY"

# 2. 检查向量库中的数据
curl http://localhost:6333/collections/kb_shared/points/count

# 3. 测试简单查询
curl -X POST http://localhost:8020/v1/retrieve \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "knowledge_base_ids": ["'$KB_ID'"], "top_k": 10}'

# 4. 检查 ACL 过滤
docker compose logs api | grep -i "acl\|security"
```

#### 解决方案

**方案1：重建向量索引**
```bash
# 删除并重新上传文档
curl -X DELETE http://localhost:8020/v1/documents/{doc_id} \
  -H "Authorization: Bearer $API_KEY"

# 重新上传文档
curl -X POST http://localhost:8020/v1/knowledge-bases/{kb_id}/documents \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "test", "content": "test content"}'
```

**方案2：检查 ACL 配置**
```bash
# 检查 API Key 的 identity 配置
docker compose exec api python -c "
from app.models.api_key import APIKey
from app.db.session import async_session_maker
import asyncio
async def check():
    async with async_session_maker() as session:
        api_key = await session.get(APIKey, 'key_id')
        print('Identity:', api_key.identity if api_key else 'Not found')
asyncio.run(check())
"

# 检查文档的 ACL 设置
curl -X GET http://localhost:8020/v1/documents/{doc_id} \
  -H "Authorization: Bearer $API_KEY"
```

**方案3：调整检索参数**
```bash
# 降低相似度阈值
curl -X POST http://localhost:8020/v1/retrieve \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test", 
    "knowledge_base_ids": ["'$KB_ID'"], 
    "top_k": 20,
    "score_threshold": 0.1
  }'

# 使用不同的检索器
curl -X POST http://localhost:8020/v1/retrieve \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test", 
    "knowledge_base_ids": ["'$KB_ID'"], 
    "retriever": "dense"
  }'
```

### 3. 数据不一致

#### 症状
- 文档显示已上传但检索不到
- Chunk 数量与预期不符
- 向量库和数据库数据不匹配

#### 诊断步骤

```bash
# 1. 比较数据库和向量库的数据量
# 数据库中的 chunk 数量
docker compose exec db psql -U kb -d kb -c "
SELECT kb.name, COUNT(c.id) as chunk_count 
FROM knowledge_bases kb 
LEFT JOIN documents d ON d.knowledge_base_id = kb.id 
LEFT JOIN chunks c ON c.document_id = d.id 
GROUP BY kb.id, kb.name;"

# 向量库中的点数量
curl http://localhost:6333/collections/kb_shared/points/count

# 2. 检查索引状态
docker compose exec db psql -U kb -d kb -c "
SELECT indexing_status, COUNT(*) 
FROM chunks 
GROUP BY indexing_status;"

# 3. 查找失败的索引
docker compose exec db psql -U kb -d kb -c "
SELECT id, indexing_error 
FROM chunks 
WHERE indexing_status = 'failed' 
LIMIT 10;"
```

#### 解决方案

**方案1：重新索引失败的 chunks**
```bash
# 重试失败的 chunks
docker compose exec api python -c "
from app.services.ingestion import retry_failed_chunks
from app.db.session import async_session_maker
import asyncio
async def retry():
    async with async_session_maker() as session:
        result = await retry_failed_chunks(session)
        print(f'Retried {result} chunks')
asyncio.run(retry())
"
```

**方案2：数据一致性修复**
```bash
# 清理孤立的向量数据
curl -X POST http://localhost:6333/collections/kb_shared/points/delete \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must_not": [
        {"key": "chunk_id", "match": {"any": ["existing_chunk_ids"]}}
      ]
    }
  }'

# 重建所有索引（谨慎操作）
docker compose exec api python -c "
from app.services.ingestion import rebuild_all_indexes
import asyncio
asyncio.run(rebuild_all_indexes())
"
```

## 性能问题

### 1. 检索延迟高

#### 症状
- 检索请求 > 5秒
- 用户体验差

#### 诊断步骤

```bash
# 1. 测试检索性能
time curl -X POST http://localhost:8020/v1/retrieve \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "knowledge_base_ids": ["'$KB_ID'"]}'

# 2. 分析各组件延迟
# 向量库查询
time curl -X POST http://localhost:6333/collections/kb_shared/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.2], "limit": 10}'

# 数据库查询
time docker compose exec db psql -U kb -d kb -c "
SELECT * FROM chunks WHERE knowledge_base_id = '$KB_ID' LIMIT 10;"

# 3. 检查系统负载
iostat -x 1 5
sar -u 1 5
```

#### 解决方案

**方案1：优化向量库配置**
```bash
# 调整 HNSW 参数
curl -X PUT http://localhost:6333/collections/kb_shared \
  -H "Content-Type: application/json" \
  -d '{
    "hnsw_config": {
      "m": 16,
      "ef_construct": 100,
      "full_scan_threshold": 10000
    }
  }'
```

**方案2：启用缓存**
```bash
# 启用检索缓存
ENABLE_RETRIEVAL_CACHE=true
RETRIEVAL_CACHE_TTL=300

# 启用 Embedding 缓存
ENABLE_EMBEDDING_CACHE=true
EMBEDDING_CACHE_TTL=3600
```

**方案3：数据库优化**
```sql
-- 添加索引
CREATE INDEX CONCURRENTLY idx_chunks_kb_vector ON chunks(knowledge_base_id) 
WHERE indexing_status = 'indexed';

-- 更新统计信息
ANALYZE chunks;
```

### 2. LLM 调用超时

#### 症状
```
openai.APITimeoutError: Request timed out
Connection timeout to LLM service
```

#### 诊断步骤

```bash
# 1. 测试网络连通性
ping api.openai.com
curl -I https://api.openai.com

# 2. 测试 API Key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# 3. 测试本地服务
curl http://localhost:11434/api/tags

# 4. 检查代理设置
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

#### 解决方案

**方案1：调整超时配置**
```bash
# 增加超时时间
LLM_TIMEOUT=60
OPENAI_TIMEOUT=60

# 启用重试
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=1
```

**方案2：使用本地模型**
```bash
# 启动本地 Ollama
docker compose up -d ollama

# 下载模型
docker compose exec ollama ollama pull qwen3:14b

# 切换到本地模型
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:14b
```

**方案3：配置代理**
```bash
# 设置代理（如果需要）
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
NO_PROXY=localhost,127.0.0.1,db,qdrant,redis
```

## 安全问题

### 1. 认证失败

#### 症状
```json
{"detail": "Invalid API key", "code": "INVALID_API_KEY"}
```

#### 诊断步骤

```bash
# 1. 检查 API Key 格式
echo $API_KEY | wc -c  # 应该 > 20 字符

# 2. 验证 API Key 存在
docker compose exec db psql -U kb -d kb -c "
SELECT id, name, role, is_active 
FROM api_keys 
WHERE key_hash = encode(sha256('$API_KEY'::bytea), 'hex');"

# 3. 检查 API Key 状态
curl -X GET http://localhost:8020/v1/api-keys \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

#### 解决方案

**方案1：重新生成 API Key**
```bash
# 使用管理员 Token 创建新的 API Key
curl -X POST http://localhost:8020/admin/tenants/{tenant_id}/api-keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "new-key", "role": "admin"}'
```

**方案2：修复 API Key 状态**
```bash
# 激活被禁用的 API Key
docker compose exec db psql -U kb -d kb -c "
UPDATE api_keys 
SET is_active = true 
WHERE id = 'key_id';"
```

### 2. 权限不足

#### 症状
```json
{"detail": "Insufficient permissions", "code": "NO_PERMISSION"}
```

#### 诊断步骤

```bash
# 1. 检查 API Key 角色
curl -X GET http://localhost:8020/v1/api-keys \
  -H "Authorization: Bearer $API_KEY"

# 2. 检查知识库权限
docker compose exec db psql -U kb -d kb -c "
SELECT ak.name, ak.role, ak.scope_kb_ids 
FROM api_keys ak 
WHERE ak.key_hash = encode(sha256('$API_KEY'::bytea), 'hex');"

# 3. 检查文档 ACL
curl -X GET http://localhost:8020/v1/documents/{doc_id} \
  -H "Authorization: Bearer $API_KEY"
```

#### 解决方案

**方案1：提升 API Key 权限**
```bash
# 升级为 admin 角色
curl -X PATCH http://localhost:8020/v1/api-keys/{key_id} \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

**方案2：调整知识库范围**
```bash
# 扩展 scope_kb_ids
curl -X PATCH http://localhost:8020/v1/api-keys/{key_id} \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scope_kb_ids": ["kb1", "kb2", "kb3"]}'
```

**方案3：修改文档 ACL**
```bash
# 更新文档访问权限
docker compose exec db psql -U kb -d kb -c "
UPDATE documents 
SET acl_allow_users = array['user1', 'user2'],
    acl_allow_roles = array['admin', 'user']
WHERE id = 'doc_id';"
```

## 日志分析

### 常用日志查询

```bash
# 错误日志
docker compose logs api | grep ERROR

# 慢请求（> 5秒）
docker compose logs api | grep -E "duration_ms.*[5-9][0-9][0-9][0-9]"

# 认证失败
docker compose logs api | grep -E "INVALID_API_KEY|UNAUTHORIZED"

# 数据库错误
docker compose logs api | grep -E "sqlalchemy|asyncpg"

# 向量库错误
docker compose logs api | grep -E "qdrant|vector"

# LLM 调用错误
docker compose logs api | grep -E "openai|ollama|llm"
```

### 日志级别调整

```bash
# 临时调整日志级别
LOG_LEVEL=DEBUG docker compose up api

# 启用 SQL 查询日志
DATABASE_ECHO=true docker compose up api

# 启用详细的 HTTP 日志
UVICORN_LOG_LEVEL=debug docker compose up api
```

## 监控告警

### 关键指标监控

```bash
# 服务可用性
curl -f http://localhost:8020/health || echo "Service Down"

# 响应时间
curl -w "%{time_total}" -o /dev/null -s http://localhost:8020/health

# 错误率
docker compose logs api --since 1h | grep ERROR | wc -l

# 资源使用
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### 自动化监控脚本

```bash
#!/bin/bash
# monitor.sh

# 检查服务健康状态
check_health() {
    local service=$1
    local url=$2
    
    if curl -f -s "$url" > /dev/null; then
        echo "✓ $service is healthy"
    else
        echo "✗ $service is down"
        # 发送告警
        # send_alert "$service is down"
    fi
}

# 检查各个服务
check_health "API" "http://localhost:8020/health"
check_health "Qdrant" "http://localhost:6333/health"

# 检查数据库连接
if docker compose exec -T db psql -U kb -d kb -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ Database is healthy"
else
    echo "✗ Database is down"
fi

# 检查磁盘空间
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠ Disk usage is high: ${DISK_USAGE}%"
fi

# 检查内存使用
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -gt 80 ]; then
    echo "⚠ Memory usage is high: ${MEM_USAGE}%"
fi
```

## 应急处理

### 服务完全不可用

```bash
# 1. 快速重启所有服务
docker compose down
docker compose up -d

# 2. 检查服务状态
docker compose ps
docker compose logs -f

# 3. 如果仍有问题，重建服务
docker compose down -v  # 注意：会删除数据
docker compose build --no-cache
docker compose up -d
```

### 数据库损坏

```bash
# 1. 停止服务
docker compose stop api

# 2. 备份当前数据
docker compose exec db pg_dump -U kb kb > emergency_backup.sql

# 3. 检查数据库完整性
docker compose exec db psql -U kb -d kb -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public';"

# 4. 如果需要，从备份恢复
docker compose down
docker volume rm self-rag-pipeline_postgres_data
docker compose up -d db
# 等待数据库启动
cat emergency_backup.sql | docker compose exec -T db psql -U kb -d kb
```

### 向量库数据丢失

```bash
# 1. 检查是否有快照备份
curl http://localhost:6333/collections/kb_shared/snapshots

# 2. 如果有备份，恢复快照
curl -X PUT "http://localhost:6333/collections/kb_shared/snapshots/upload" \
  --form file=@snapshot.tar

# 3. 如果没有备份，重建向量索引
docker compose exec api python -c "
from app.services.ingestion import rebuild_vector_index
import asyncio
asyncio.run(rebuild_vector_index())
"
```

---

如果以上方法都无法解决问题，请联系技术支持团队，并提供：
1. 详细的错误信息和日志
2. 系统配置信息
3. 重现问题的步骤
4. 系统资源使用情况