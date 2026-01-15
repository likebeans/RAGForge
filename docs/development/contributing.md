# 贡献指南

欢迎贡献代码与文档！本指南涵盖本地环境、测试、规范与 PR 检查项。

## 本地环境

### 环境要求

- Python 3.11+
- 推荐使用 [`uv`](https://github.com/astral-sh/uv) 进行依赖管理
- Docker 和 Docker Compose（用于基础设施服务）

### 快速开始

1. **安装依赖**：
   ```bash
   uv sync
   ```

2. **启动基础设施服务**：
   ```bash
   # 启动 PostgreSQL + Qdrant
   docker compose up -d db qdrant
   
   # 如果需要验证 ES/OpenSearch 稀疏检索
   docker compose -f docker-compose.opensearch.yml up -d
   ```

3. **配置环境变量**：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，设置以下关键配置：
   # - DATABASE_URL
   # - ADMIN_TOKEN
   # - 模型 API Keys (OPENAI_API_KEY, OLLAMA_BASE_URL 等)
   ```

4. **初始化数据库**：
   ```bash
   uv run alembic upgrade head
   ```

5. **启动 API 服务**（本地热重载）：
   ```bash
   uv run uvicorn app.main:app --reload --port 8020
   ```

6. **启动前端控制台**（可选）：
   ```bash
   docker compose up -d frontend
   # 浏览器访问 http://localhost:3003
   ```

## 常用开发命令

### 代码质量检查

```bash
# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check .

# 类型检查
uv run mypy app/ sdk/
```

### 测试

```bash
# 运行单元测试
uv run pytest tests/ -v

# 端到端测试（需要运行中的服务与 API Key）
API_BASE=http://localhost:8020 API_KEY=xxx uv run pytest test/test_live_e2e.py -v

# 运行特定测试文件
uv run pytest tests/test_chunkers.py -v

# 运行带覆盖率的测试
uv run pytest tests/ --cov=app --cov-report=html
```

### 数据库操作

```bash
# 创建数据库迁移
uv run alembic revision --autogenerate -m "描述变更内容"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1

# 查看迁移历史
uv run alembic history
```

### BM25 索引管理

```bash
# 从数据库重建指定租户的 BM25 索引
uv run python scripts/rebuild_bm25.py --tenant <tenant_id>

# 只重建某个知识库的 BM25 索引
uv run python scripts/rebuild_bm25.py --tenant <tenant_id> --kb <kb_id>

# 迁移/双写到 Elasticsearch
uv run python scripts/migrate_bm25_to_es.py --tenant <tenant_id> [--kb <kb_id>] --backend es

# 管理 Elasticsearch 索引（列出/删除/刷新）
uv run python scripts/manage_es_indices.py list --prefix kb_
uv run python scripts/manage_es_indices.py delete --index kb_test
uv run python scripts/manage_es_indices.py refresh --index kb_prod
```

## 开发规范

### 代码规范

- **注释语言**：使用中文注释，便于团队阅读
- **类型提示**：所有函数必须有完整的类型标注
- **异步优先**：数据库和 HTTP 操作使用 async/await
- **错误处理**：使用 HTTPException 返回标准错误格式

### 命名规范

- **ORM 字段命名**：避免使用 `metadata`（SQLAlchemy 保留字），使用 `extra_metadata` 并显式指定列名
- **API 路由**：使用 RESTful 风格，遵循现有路径结构
- **函数命名**：使用动词开头，如 `create_knowledge_base`、`get_document_by_id`

### 分支管理

- **主分支**：`main` 为稳定分支，用于生产部署
- **功能分支**：从 `main` 创建 `feature/<topic>` 分支进行开发
- **修复分支**：从 `main` 创建 `fix/<issue>` 分支进行 bug 修复
- **提交信息**：建议使用 Conventional Commits 格式（feat/fix/docs/chore/test/refactor）

### API 变更规范

当进行 API 变更时，需要同步更新：

1. **Pydantic Schema**：更新请求/响应模型
2. **OpenAPI 文档**：自动生成，确保 schema 正确
3. **SDK 示例**：更新 Python SDK 的使用示例
4. **前端契约**：通知前端团队 API 变更

### Pipeline 扩展规范

新增 chunker/retriever 时的步骤：

1. **实现算法类**：继承相应的基类
2. **注册到 registry**：在 `operator_registry` 中注册
3. **添加测试**：编写单元测试和集成测试
4. **更新文档**：补充 `app/pipeline/*/README.md` 中的使用示例

## 测试规范

### 测试分类

- **单元测试**：测试单个函数或类的功能
- **集成测试**：测试多个组件的协作
- **端到端测试**：测试完整的 API 流程

### 测试数据

- 使用 pytest fixtures 管理测试数据
- 测试数据应该是确定性的，避免随机性
- 清理测试数据，避免影响其他测试

### Mock 使用

- 对外部服务（LLM API、向量数据库）进行 mock
- 使用 `pytest-mock` 或 `unittest.mock`
- 确保 mock 的行为与真实服务一致

## PR 检查清单

提交 Pull Request 前，请确保：

- [ ] **代码质量**：通过 `ruff format` + `ruff check` + `mypy` 检查
- [ ] **测试通过**：单元/集成测试全部通过，必要时补充新的测试用例
- [ ] **数据库迁移**：如有数据库变更，包含 Alembic 迁移并验证升级/降级
- [ ] **文档更新**：更新相关文档（README/ARCHITECTURE/SECURITY/SDK 示例）
- [ ] **配置管理**：新增配置项有默认值与 `.env.example` 注释，敏感信息不入库/不入 Git
- [ ] **性能影响**：性能/安全敏感改动写明影响面与回滚策略
- [ ] **向后兼容**：API 变更保持向后兼容，或提供迁移指南

## 问题报告

### 提交 Issue

报告问题时，请提供：

- **复现步骤**：详细的操作步骤
- **预期结果**：期望的行为
- **实际结果**：实际发生的情况
- **环境信息**：操作系统、Python 版本、依赖版本
- **日志/截图**：相关的错误日志或截图
- **影响范围**：影响的租户/知识库范围

### 安全问题

安全相关问题请通过私有渠道报告，详见 `docs/SECURITY.md` 中的漏洞上报流程。

## 开发环境配置

### 推荐的开发工具

- **IDE**：VS Code 或 PyCharm
- **Python 环境管理**：uv 或 pyenv
- **数据库客户端**：DBeaver 或 pgAdmin
- **API 测试**：Postman 或 curl
- **向量数据库管理**：Qdrant Web UI (http://localhost:6333/dashboard)

### VS Code 配置

推荐的 `.vscode/settings.json` 配置：

```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "python.linting.mypyEnabled": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### 环境变量模板

`.env.example` 文件包含了所有必要的环境变量模板，开发时请复制并根据实际情况修改：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/kb

# 管理员令牌
ADMIN_TOKEN=your-secure-admin-token

# LLM 配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:14b
OLLAMA_BASE_URL=http://localhost:11434

# Embedding 配置
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024

# 向量数据库配置
QDRANT_URL=http://localhost:6333
QDRANT_ISOLATION_STRATEGY=partition
```

## 性能优化建议

### 数据库优化

- 使用连接池，避免频繁创建连接
- 合理使用索引，特别是查询频繁的字段
- 使用 `select_related` 和 `joinedload` 减少 N+1 查询
- 批量操作使用 `bulk_insert_mappings` 等方法

### 向量数据库优化

- 批量写入向量，避免单条插入
- 合理设置 Collection 的 `hnsw_config` 参数
- 使用适当的向量维度，平衡精度和性能

### 缓存策略

- 对频繁查询的配置信息使用缓存
- 使用 Redis 进行分布式缓存
- 合理设置缓存过期时间

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查 PostgreSQL 服务是否启动
   - 验证 `DATABASE_URL` 配置是否正确
   - 确认数据库用户权限

2. **向量数据库连接失败**
   - 检查 Qdrant 服务是否启动
   - 验证 `QDRANT_URL` 配置
   - 查看 Qdrant 日志

3. **LLM API 调用失败**
   - 检查 API Key 是否有效
   - 验证网络连接
   - 查看 API 限流状态

### 日志调试

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
export LOG_JSON=true
uv run uvicorn app.main:app --reload --port 8020
```

查看特定模块的日志：

```python
import logging
logging.getLogger("app.services.ingestion").setLevel(logging.DEBUG)
```

## 贡献流程

1. **Fork 项目**：在 GitHub 上 fork 项目到个人账户
2. **创建分支**：从 `main` 创建功能分支
3. **开发功能**：按照规范进行开发
4. **测试验证**：确保所有测试通过
5. **提交 PR**：创建 Pull Request 并填写详细描述
6. **代码审查**：响应审查意见，完善代码
7. **合并代码**：审查通过后合并到主分支

感谢您的贡献！