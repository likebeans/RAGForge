# 贡献指南

欢迎贡献代码与文档！本指南涵盖本地环境、测试、规范与 PR 检查项。

## 本地环境
1. 安装 Python 3.11+，推荐使用 [`uv`](https://github.com/astral-sh/uv)。
2. 安装依赖：
   ```bash
   uv sync
   ```
3. 启动依赖服务（PostgreSQL + Qdrant）：
   ```bash
   docker compose up -d db qdrant
   ```
   如果需要验证 ES/OpenSearch 稀疏检索：
   ```bash
   docker compose -f docker-compose.opensearch.yml up -d
   ```
4. 配置环境变量：
   ```bash
   cp .env.example .env
   # 设置 DATABASE_URL, ADMIN_TOKEN, 模型 API Keys 等
   ```
5. 初始化数据库：
   ```bash
   uv run alembic upgrade head
   ```
6. 启动 API（本地热重载）：
   ```bash
   uv run uvicorn app.main:app --reload --port 8020
   ```
7. 前端控制台（容器化运行）：
   ```bash
   docker compose up -d frontend
   # 浏览器访问 http://localhost:3003
   ```

## 常用命令
- 代码检查与格式化：
  ```bash
  uv run ruff format .
  uv run ruff check .
  uv run mypy app/ sdk/
  ```
- 测试：
  ```bash
  uv run pytest tests/ -v
  # 端到端（需要运行中的服务与 API Key）
  API_BASE=http://localhost:8020 API_KEY=xxx uv run pytest test/test_live_e2e.py -v
  ```
- 数据库迁移：
  ```bash
  uv run alembic revision --autogenerate -m "desc"
  uv run alembic upgrade head
  ```
- BM25 重建（内存索引，生产建议关闭或替换 ES/OpenSearch）：
  ```bash
  # 从数据库重建指定租户的 BM25 索引
  uv run python scripts/rebuild_bm25.py --tenant <tenant_id>
  # 只重建某个 KB
  uv run python scripts/rebuild_bm25.py --tenant <tenant_id> --kb <kb_id>
  # 迁移/双写到 ES
  uv run python scripts/migrate_bm25_to_es.py --tenant <tenant_id> [--kb <kb_id>] --backend es
  # 管理 ES 索引（列出/删除/刷新）
  uv run python scripts/manage_es_indices.py list --prefix kb_
  ```

## 代码与分支规范
- 分支：`main` 稳定；功能从 `feature/<topic>` 或 `fix/<topic>` 起分支。
- 提交信息：建议使用 Conventional Commits（feat/fix/docs/chore/test/refactor）。
- API 变更需要同步更新：Pydantic schema、OpenAPI 文档（自动）、SDK 示例、前端契约。
- Pipeline 扩展：新增 chunker/retriever 时请注册到 `operator_registry`，并补充 `app/pipeline/*/AGENTS.md` 示例。

## PR Checklist
- [ ] 代码通过 `ruff format` + `ruff check` + `mypy`。
- [ ] 单元/集成测试通过，必要时补充新的测试用例。
- [ ] 如有数据库变更，包含 Alembic 迁移并验证升级/降级。
- [ ] 更新相关文档（README/ARCHITECTURE/SECURITY/SDK 示例）。
- [ ] 新增配置项有默认值与 `.env.example` 注释，敏感信息不入库/不入 Git。
- [ ] 性能/安全敏感改动写明影响面与回滚策略。

## 提交 Issue
- 请描述：复现步骤、预期结果、实际结果、日志/截图、影响范围（租户/KB）。
- 安全问题请走私有渠道（见 `docs/SECURITY.md` 漏洞上报）。
