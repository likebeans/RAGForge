# 生产环境部署检查清单

**快速检查**: 部署前必须完成的关键步骤

---

## ⚠️ 必须修改的配置

### 1. 密钥和密码 🔐
```bash
# .env 文件中必须修改

✅ ADMIN_TOKEN=生产环境的安全令牌（使用 Admin Token API 生成）
✅ DATABASE_URL 中的数据库密码
✅ REDIS_URL 中的 Redis 密码（如果启用）
✅ QDRANT_API_KEY=生成的安全密钥（如果启用）
✅ 所有模型提供商的真实 API Keys（QWEN_API_KEY 等）
```

### 2. CORS 配置 🌐
```python
# app/main.py 第 51 行左右

❌ 开发环境:
allow_origins=["*"]  # 不安全！

✅ 生产环境:
allow_origins=[
    "https://your-frontend-domain.com",
    "https://app.your-domain.com",
]
```

### 3. 日志级别 📊
```bash
# .env
LOG_LEVEL=INFO  # 不要用 DEBUG
```

---

## 📋 部署步骤

### 步骤 1: 服务器准备
```bash
# 1. 检查服务器配置
- CPU: 4 核以上
- 内存: 16 GB 以上
- 磁盘: 100 GB SSD 以上

# 2. 安装依赖
sudo apt update
sudo apt install -y docker.io docker-compose nginx certbot
```

### 步骤 2: 配置文件
```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 修改 .env 中的所有密钥
vim .env

# 3. 修改 CORS 配置
vim app/main.py
```

### 步骤 3: SSL 证书
```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d api.your-domain.com
```

### 步骤 4: 数据库迁移
```bash
# 1. 启动数据库
docker-compose up -d db

# 2. 运行迁移
DATABASE_URL=postgresql+asyncpg://kb:<password>@localhost:5435/kb \
uv run alembic upgrade head
```

### 步骤 5: 启动服务
```bash
# 1. 构建镜像
docker-compose build

# 2. 启动所有服务
docker-compose up -d

# 3. 检查状态
docker-compose ps
```

### 步骤 6: 验证部署
```bash
# 1. 健康检查
curl http://localhost:8020/health

# 2. 创建 Admin Token
curl -X POST http://localhost:8020/admin/tokens \
  -H "X-Admin-Token: <临时token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production Admin", "description": "生产环境"}'

# 3. 创建测试租户
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: <新生成的token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Tenant"}'
```

### 步骤 7: 配置备份
```bash
# 1. 创建备份脚本
sudo mkdir -p /opt/backup
sudo cp scripts/backup.sh /opt/backup/

# 2. 添加定时任务
crontab -e
# 添加: 0 2 * * * /opt/backup/backup.sh
```

---

## ✅ 部署后检查

### 核心功能测试
- [ ] API 健康检查返回 200
- [ ] 数据库连接正常
- [ ] Redis 缓存正常
- [ ] Qdrant 向量库正常
- [ ] 创建租户成功
- [ ] 创建知识库成功
- [ ] 上传文档成功
- [ ] 检索功能正常
- [ ] RAG 生成正常

### 安全检查
- [ ] 所有密钥已修改
- [ ] CORS 已限制
- [ ] HTTPS 已配置
- [ ] 防火墙已设置
- [ ] SSH 密钥登录已启用

### 监控检查
- [ ] 日志正常输出
- [ ] 日志轮转已配置
- [ ] 备份脚本已测试
- [ ] 健康检查端点可访问
- [ ] 性能监控已启用（可选）

---

## 🚨 常见问题

### 数据库连接失败
```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker logs rag_kb_postgres

# 测试连接
docker exec -it rag_kb_postgres psql -U kb -d kb
```

### Redis 连接失败
```bash
# 检查容器
docker-compose ps redis

# 测试连接
docker exec -it rag_kb_redis redis-cli PING
```

### API 启动失败
```bash
# 查看 API 日志
docker logs rag_kb_api

# 检查环境变量
docker-compose config
```

---

## 📞 紧急回滚

```bash
# 1. 停止服务
docker-compose down

# 2. 恢复配置
cp .env.backup.<date> .env

# 3. 恢复数据库
gunzip -c /backup/postgres/kb_<date>.sql.gz | \
    docker exec -i rag_kb_postgres psql -U kb kb

# 4. 重启
docker-compose up -d
```

---

## 📚 参考文档

- **详细部署指南**: `PRODUCTION_DEPLOYMENT_GUIDE.md`
- **代码改进总结**: `CODE_REVIEW_IMPROVEMENTS_SUMMARY.md`
- **Admin Token 迁移**: `ADMIN_TOKEN_MIGRATION_GUIDE.md`
- **测试报告**: `TEST_SUMMARY.md`

---

**完成时间估计**: 2-4 小时（首次部署）

**建议**: 先在测试环境部署一次，确保流程顺畅后再部署到生产环境。
