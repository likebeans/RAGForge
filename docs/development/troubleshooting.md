# 开发问题排查指南

本文档整理了 Self-RAG Pipeline 开发过程中常见问题的排查方法和解决方案。

## 环境配置问题

### Python 环境问题

#### 问题：uv sync 失败

**症状**：
```bash
uv sync
# 报错：Failed to resolve dependencies
```

**排查步骤**：
1. 检查 Python 版本：
   ```bash
   python --version  # 需要 3.11+
   uv python list
   ```

2. 清理缓存：
   ```bash
   uv cache clean
   rm -rf .venv
   uv sync
   ```

3. 检查网络连接：
   ```bash
   # 测试 PyPI 连接
   curl -I https://pypi.org/
   ```

**解决方案**：
- 升级到 Python 3.11+
- 配置代理或镜像源
- 使用 `uv sync --no-cache` 强制重新下载

#### 问题：导入模块失败

**症状**：
```python
ModuleNotFoundError: No module named 'app'
```

**排查步骤**：
1. 检查虚拟环境：
   ```bash
   which python
   # 应该指向 .venv/bin/python
   ```

2. 检查 PYTHONPATH：
   ```bash
   echo $PYTHONPATH
   # 应该包含项目根目录
   ```

3. 激活虚拟环境：
   ```bash
   source .venv/bin/activate
   # 或使用 uv run
   uv run python -c "import app; print('OK')"
   ```

**解决方案**：
- 使用 `uv run` 前缀执行命令
- 在 IDE 中正确配置 Python 解释器路径
- 检查项目根目录是否在 sys.path 中

### 数据库连接问题

#### 问题：PostgreSQL 连接失败

**症状**：
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
connection to server at "localhost", port 5435 failed
```

**排查步骤**：
1. 检查 PostgreSQL 服务状态：
   ```bash
   docker compose ps db
   # 或
   pg_isready -h localhost -p 5435
   ```

2. 检查端口占用：
   ```bash
   netstat -tlnp | grep 5435
   lsof -i :5435
   ```

3. 检查数据库配置：
   ```bash
   echo $DATABASE_URL
   # 应该是：postgresql+asyncpg://kb:kb@localhost:5435/kb
   ```

4. 测试连接：
   ```bash
   psql -h localhost -p 5435 -U kb -d kb
   ```

**解决方案**：
- 启动 PostgreSQL 服务：`docker compose up -d db`
- 检查防火墙设置
- 验证用户名密码和数据库名
- 检查 Docker 网络配置

#### 问题：数据库迁移失败

**症状**：
```bash
uv run alembic upgrade head
# 报错：Target database is not up to date
```

**排查步骤**：
1. 检查迁移历史：
   ```bash
   uv run alembic history
   uv run alembic current
   ```

2. 检查数据库表：
   ```sql
   \dt  -- 列出所有表
   SELECT * FROM alembic_version;
   ```

3. 检查迁移文件：
   ```bash
   ls alembic/versions/
   ```

**解决方案**：
- 重置数据库：`docker compose down -v && docker compose up -d db`
- 手动标记版本：`uv run alembic stamp head`
- 逐步升级：`uv run alembic upgrade +1`
- 检查迁移文件冲突

### 向量数据库问题

#### 问题：Qdrant 连接失败

**症状**：
```
qdrant_client.http.exceptions.UnexpectedResponse: 
Unexpected response: 404 page not found
```

**排查步骤**：
1. 检查 Qdrant 服务：
   ```bash
   docker compose ps qdrant
   curl http://localhost:6333/health
   ```

2. 检查 Collection 状态：
   ```bash
   curl http://localhost:6333/collections
   ```

3. 检查配置：
   ```bash
   echo $QDRANT_URL
   # 应该是：http://localhost:6333
   ```

**解决方案**：
- 启动 Qdrant 服务：`docker compose up -d qdrant`
- 检查端口映射：`docker compose logs qdrant`
- 重建 Collection：删除 Qdrant 数据卷

#### 问题：向量维度不匹配

**症状**：
```
qdrant_client.http.exceptions.UnexpectedResponse: 
Wrong vector dimension: expected 1024, got 1536
```

**排查步骤**：
1. 检查 Embedding 配置：
   ```bash
   echo $EMBEDDING_MODEL
   echo $EMBEDDING_DIM
   ```

2. 检查 Collection 配置：
   ```bash
   curl http://localhost:6333/collections/kb_shared
   ```

3. 检查已有数据：
   ```sql
   SELECT COUNT(*) FROM chunks WHERE tenant_id = 'your_tenant_id';
   ```

**解决方案**：
- 统一向量维度配置
- 删除不匹配的 Collection：
  ```bash
  curl -X DELETE http://localhost:6333/collections/kb_shared
  ```
- 重新入库所有文档

## API 服务问题

### 启动失败

#### 问题：端口被占用

**症状**：
```bash
uvicorn app.main:app --port 8020
# 报错：[Errno 48] Address already in use
```

**排查步骤**：
1. 检查端口占用：
   ```bash
   lsof -i :8020
   netstat -tlnp | grep 8020
   ```

2. 查找进程：
   ```bash
   ps aux | grep uvicorn
   ```

**解决方案**：
- 杀死占用进程：`kill -9 <PID>`
- 使用其他端口：`--port 8021`
- 检查是否有其他实例在运行

#### 问题：模块导入错误

**症状**：
```bash
uvicorn app.main:app
# 报错：ModuleNotFoundError: No module named 'app.main'
```

**排查步骤**：
1. 检查当前目录：
   ```bash
   pwd
   ls -la app/
   ```

2. 检查 main.py 文件：
   ```bash
   ls -la app/main.py
   ```

3. 测试导入：
   ```bash
   uv run python -c "from app.main import app; print('OK')"
   ```

**解决方案**：
- 确保在项目根目录执行
- 使用 `uv run uvicorn app.main:app`
- 检查 `app/__init__.py` 文件存在

### 运行时错误

#### 问题：LLM API 调用失败

**症状**：
```
openai.APIConnectionError: Connection error
```

**排查步骤**：
1. 检查 API 配置：
   ```bash
   echo $OPENAI_API_KEY
   echo $OPENAI_API_BASE
   echo $LLM_PROVIDER
   ```

2. 测试 API 连接：
   ```bash
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        "$OPENAI_API_BASE/models"
   ```

3. 检查 Ollama 服务（如果使用）：
   ```bash
   curl http://localhost:11434/api/tags
   ```

**解决方案**：
- 验证 API Key 有效性
- 检查网络连接和代理设置
- 启动 Ollama 服务：`ollama serve`
- 检查模型是否已下载：`ollama list`

#### 问题：Embedding 生成失败

**症状**：
```
RuntimeError: Embedding generation failed
```

**排查步骤**：
1. 检查 Embedding 配置：
   ```bash
   echo $EMBEDDING_PROVIDER
   echo $EMBEDDING_MODEL
   ```

2. 测试 Embedding API：
   ```bash
   curl -X POST "$OLLAMA_BASE_URL/api/embeddings" \
        -d '{"model": "bge-m3", "prompt": "test"}'
   ```

3. 检查模型可用性：
   ```bash
   ollama list | grep bge-m3
   ```

**解决方案**：
- 下载 Embedding 模型：`ollama pull bge-m3`
- 检查模型名称拼写
- 验证 API 端点可访问性

## 功能测试问题

### 文档入库问题

#### 问题：文档切分失败

**症状**：
```
ValueError: Chunker 'markdown' not found in registry
```

**排查步骤**：
1. 检查切分器注册：
   ```python
   from app.pipeline import operator_registry
   print(operator_registry.list_operators("chunker"))
   ```

2. 检查配置：
   ```python
   kb_config = {"ingestion": {"chunker": {"name": "markdown"}}}
   ```

3. 检查导入：
   ```python
   from app.pipeline.chunkers import markdown
   ```

**解决方案**：
- 确保切分器已正确注册
- 检查切分器名称拼写
- 验证切分器模块导入

#### 问题：向量化失败

**症状**：
```
Exception: Failed to generate embeddings for chunk
```

**排查步骤**：
1. 检查文本内容：
   ```python
   print(f"Chunk length: {len(chunk_text)}")
   print(f"Chunk content: {chunk_text[:100]}...")
   ```

2. 检查 Embedding 服务：
   ```bash
   curl -X POST "$EMBEDDING_API_URL" \
        -H "Content-Type: application/json" \
        -d '{"input": "test text"}'
   ```

3. 检查错误日志：
   ```bash
   docker compose logs api | grep -i embedding
   ```

**解决方案**：
- 检查文本长度限制
- 验证 Embedding 模型支持的语言
- 处理特殊字符和编码问题

### 检索问题

#### 问题：检索结果为空

**症状**：
```json
{"results": [], "total": 0}
```

**排查步骤**：
1. 检查数据是否存在：
   ```sql
   SELECT COUNT(*) FROM chunks WHERE tenant_id = 'xxx';
   SELECT COUNT(*) FROM documents WHERE tenant_id = 'xxx';
   ```

2. 检查向量数据：
   ```bash
   curl "http://localhost:6333/collections/kb_shared/points/scroll" \
        -X POST -H "Content-Type: application/json" \
        -d '{"limit": 10}'
   ```

3. 测试简单查询：
   ```bash
   curl -X POST "$API_BASE/v1/retrieve" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"query": "test", "knowledge_base_ids": ["'$KB_ID'"], "top_k": 10}'
   ```

**解决方案**：
- 确认文档已成功入库
- 检查租户 ID 和知识库 ID
- 验证向量数据完整性
- 调整检索参数（降低 score_threshold）

#### 问题：检索性能差

**症状**：检索响应时间超过 5 秒

**排查步骤**：
1. 检查数据量：
   ```sql
   SELECT 
       kb.name,
       COUNT(c.id) as chunk_count,
       AVG(LENGTH(c.text)) as avg_length
   FROM knowledge_bases kb
   LEFT JOIN documents d ON d.knowledge_base_id = kb.id
   LEFT JOIN chunks c ON c.document_id = d.id
   GROUP BY kb.id, kb.name;
   ```

2. 检查索引：
   ```sql
   \d+ chunks  -- 查看索引
   ```

3. 分析查询计划：
   ```sql
   EXPLAIN ANALYZE SELECT * FROM chunks WHERE tenant_id = 'xxx';
   ```

**解决方案**：
- 添加数据库索引
- 优化向量检索参数
- 使用分页减少数据量
- 考虑缓存策略

## 权限和安全问题

### 认证问题

#### 问题：API Key 认证失败

**症状**：
```json
{"detail": "Invalid API key", "code": "INVALID_API_KEY"}
```

**排查步骤**：
1. 检查 API Key 格式：
   ```bash
   echo $API_KEY | wc -c  # 应该是合理长度
   echo $API_KEY | head -c 10  # 检查前缀
   ```

2. 检查数据库记录：
   ```sql
   SELECT prefix, role, tenant_id FROM api_keys WHERE prefix = 'kb_sk_xx';
   ```

3. 测试认证：
   ```bash
   curl -H "Authorization: Bearer $API_KEY" \
        "$API_BASE/v1/knowledge-bases"
   ```

**解决方案**：
- 验证 API Key 完整性
- 检查 API Key 是否被撤销
- 确认请求头格式正确

#### 问题：权限被拒绝

**症状**：
```json
{"detail": "Role 'read' not allowed", "code": "PERMISSION_DENIED"}
```

**排查步骤**：
1. 检查 API Key 角色：
   ```sql
   SELECT name, role, scope_kb_ids FROM api_keys WHERE prefix = 'kb_sk_xx';
   ```

2. 检查操作权限要求：
   ```python
   # 查看路由装饰器
   @router.post("/v1/knowledge-bases")
   async def create_kb(
       context: APIKeyContext = Depends(require_role("admin", "write"))
   ):
   ```

3. 检查租户状态：
   ```sql
   SELECT status FROM tenants WHERE id = 'tenant_id';
   ```

**解决方案**：
- 使用具有适当权限的 API Key
- 创建新的 API Key 并分配正确角色
- 检查租户是否被禁用

### ACL 权限问题

#### 问题：文档访问被拒绝

**症状**：检索结果中缺少预期的文档

**排查步骤**：
1. 检查文档敏感度：
   ```sql
   SELECT title, sensitivity_level, acl_roles, acl_groups 
   FROM documents WHERE id = 'doc_id';
   ```

2. 检查用户身份：
   ```sql
   SELECT identity FROM api_keys WHERE prefix = 'kb_sk_xx';
   ```

3. 测试 ACL 匹配：
   ```python
   from app.auth.acl import check_document_access
   has_access = check_document_access(user_context, document)
   print(f"Access granted: {has_access}")
   ```

**解决方案**：
- 调整文档 ACL 设置
- 更新 API Key 的身份信息
- 使用 admin 角色进行测试

## 性能问题

### 内存使用过高

#### 问题：服务内存占用持续增长

**排查步骤**：
1. 监控内存使用：
   ```bash
   docker stats api
   ps aux | grep uvicorn
   ```

2. 检查连接池：
   ```python
   from app.db.session import engine
   print(f"Pool size: {engine.pool.size()}")
   print(f"Checked out: {engine.pool.checkedout()}")
   ```

3. 分析内存泄漏：
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... 执行操作
   snapshot = tracemalloc.take_snapshot()
   top_stats = snapshot.statistics('lineno')
   ```

**解决方案**：
- 调整数据库连接池大小
- 检查异步任务是否正确关闭
- 使用内存分析工具定位泄漏

### 数据库性能问题

#### 问题：查询响应缓慢

**排查步骤**：
1. 检查慢查询：
   ```sql
   -- 启用慢查询日志
   ALTER SYSTEM SET log_min_duration_statement = 1000;
   SELECT pg_reload_conf();
   ```

2. 分析查询计划：
   ```sql
   EXPLAIN (ANALYZE, BUFFERS) 
   SELECT * FROM chunks WHERE tenant_id = 'xxx' AND text ILIKE '%keyword%';
   ```

3. 检查索引使用：
   ```sql
   SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
   FROM pg_stat_user_indexes;
   ```

**解决方案**：
- 添加合适的索引
- 优化查询条件
- 考虑分区表
- 调整 PostgreSQL 配置

## 部署问题

### Docker 构建问题

#### 问题：Docker 构建失败

**症状**：
```bash
docker build -t api .
# 报错：Failed to solve with frontend dockerfile.v0
```

**排查步骤**：
1. 检查 Dockerfile 语法：
   ```bash
   docker build --no-cache -t api .
   ```

2. 检查基础镜像：
   ```bash
   docker pull python:3.11-slim
   ```

3. 检查网络连接：
   ```bash
   docker build --network=host -t api .
   ```

**解决方案**：
- 使用 `--no-cache` 重新构建
- 配置 Docker 代理
- 检查 Dockerfile 中的文件路径

#### 问题：容器启动失败

**症状**：
```bash
docker compose up -d
# 容器立即退出
```

**排查步骤**：
1. 查看容器日志：
   ```bash
   docker compose logs api
   docker logs <container_id>
   ```

2. 检查环境变量：
   ```bash
   docker compose config
   ```

3. 进入容器调试：
   ```bash
   docker compose run --rm api bash
   ```

**解决方案**：
- 检查环境变量配置
- 验证依赖服务启动顺序
- 调整健康检查配置

## 监控和日志

### 日志问题

#### 问题：日志级别不正确

**症状**：看不到调试信息或日志过多

**排查步骤**：
1. 检查日志配置：
   ```bash
   echo $LOG_LEVEL
   echo $LOG_JSON
   ```

2. 测试日志输出：
   ```python
   import logging
   logger = logging.getLogger("app.test")
   logger.debug("Debug message")
   logger.info("Info message")
   ```

**解决方案**：
- 设置适当的 LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）
- 配置结构化日志：`LOG_JSON=true`
- 使用日志过滤器

#### 问题：日志文件过大

**排查步骤**：
1. 检查日志文件大小：
   ```bash
   du -sh /var/log/app/
   ls -lh logs/
   ```

2. 配置日志轮转：
   ```python
   # logging.conf
   [handler_file]
   class=logging.handlers.RotatingFileHandler
   maxBytes=10485760  # 10MB
   backupCount=5
   ```

**解决方案**：
- 配置日志轮转
- 调整日志级别
- 使用外部日志收集系统

## 故障恢复

### 数据恢复

#### 问题：数据库数据丢失

**恢复步骤**：
1. 停止服务：
   ```bash
   docker compose down
   ```

2. 恢复数据库备份：
   ```bash
   pg_restore -h localhost -p 5435 -U kb -d kb backup.sql
   ```

3. 重建向量索引：
   ```bash
   uv run python scripts/rebuild_vector_index.py --tenant all
   ```

#### 问题：向量数据丢失

**恢复步骤**：
1. 检查 Qdrant 数据：
   ```bash
   curl http://localhost:6333/collections
   ```

2. 从数据库重建向量：
   ```bash
   uv run python scripts/rebuild_vectors_from_db.py
   ```

3. 验证数据完整性：
   ```bash
   curl -X POST "$API_BASE/v1/retrieve" \
        -H "Authorization: Bearer $API_KEY" \
        -d '{"query": "test", "knowledge_base_ids": ["test_kb"]}'
   ```

## 预防措施

### 监控检查清单

- [ ] API 响应时间监控
- [ ] 数据库连接池状态
- [ ] 向量数据库健康状态
- [ ] 内存和 CPU 使用率
- [ ] 错误率和异常统计
- [ ] 磁盘空间使用情况

### 定期维护

- [ ] 数据库备份（每日）
- [ ] 日志清理（每周）
- [ ] 性能指标分析（每月）
- [ ] 依赖更新检查（每月）
- [ ] 安全漏洞扫描（每季度）

### 应急预案

1. **服务不可用**：
   - 检查基础设施状态
   - 回滚到上一个稳定版本
   - 启用降级模式

2. **数据损坏**：
   - 立即停止写入操作
   - 从最近备份恢复
   - 验证数据完整性

3. **性能严重下降**：
   - 启用缓存
   - 限制并发请求
   - 扩容资源

通过遵循这些排查指南，可以快速定位和解决开发过程中遇到的各种问题。