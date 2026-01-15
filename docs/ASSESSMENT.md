# 架构与工程评审（Phase 0-4）

本文件汇总当前评审结果，便于后续修复与跟踪。

## Phase 0：项目地图
- **入口**：`main.py`（FastAPI 启动、中间件、路由注册）。
- **配置/会话**：`app/config.py`（Settings）、`app/db/session.py`（async engine/pool），`alembic/` 迁移。
- **业务服务**：`app/services/ingestion.py`、`query.py`、`rag.py`、`acl.py`。
- **Pipeline**：`app/pipeline/*`（chunkers/retrievers/transforms/enrichers/postprocessors/indexers，注册表 `operator_registry`）。
- **基础设施**：`app/infra/*`（embeddings/llm/rerank/vector_store(Qdrant)/bm25_store(内存)/llamaindex/logging/metrics）。
- **数据模型**：`app/models/*`（Tenant/APIKey/KnowledgeBase/Document/Chunk/AuditLog/...）。
- **SDK/前端**：`sdk/` 同步 Python 客户端，`frontend/` Next.js 管理/实验台。
- **部署**：`Dockerfile`（uv base），`docker-compose.yml`（api + Postgres + Qdrant），`scripts/docker-entrypoint.sh`。

## Phase 1：架构梳理
- **逻辑链路**：Client → FastAPI (`app/main.py` & routes) → Middleware (RequestTrace/Audit + Auth/RateLimit) → Services (ingestion/query/rag/acl) → Pipeline operators → Infra (embeddings/LLM/rerank/vector_store/BM25) → Storage (PostgreSQL + Qdrant + BM25 内存) → Observability (logging/metrics/audit).
- **多租户/ACL**：API Key 校验+限流（`get_api_key_context`），`scope_kb_ids`/角色过滤，DB `tenant_id` 约束；向量库 collection/partition 隔离，chunk payload 带 `sensitivity_level/acl_*`，检索后 `filter_results_by_acl` 二次修剪，无 ACL 命中返回 403 `NO_PERMISSION`。
- **边界评估**：服务层直接耦合具体存储（`vector_store/bm25_store`）；摄取承担长耗时编排；BM25 内存无替换接口；ACL 未下推向量库。
- **风险点与路线**：
  1) ACL 未下推 Qdrant，安全/性能风险 → 在 search 注入 ACL Filter，保留二次过滤。
  2) 摄取同步、长事务占用连接 → 队列化/拆事务/超时幂等。
  3) BM25 内存单实例 → 替换 ES/OpenSearch 或提供重建/持久方案。
  4) 限流/外部调用缺少异步超时熔断 → 使用异步 Redis/超时重试，并记录 metrics。

## Phase 2：代码问题清单（可开 Issue/PR）
- P0 `vector_store.search`/`services.query`: ACL 仅应用层过滤，Qdrant 未加 Filter，存在泄露风险。→ 基于 `UserContext` 构造 should(public or ACL) Filter，下推到 Qdrant，保留二次过滤并补测试。
- P1 `auth.api_key.RedisRateLimiter`: 同步 redis 客户端阻塞事件循环，无超时。→ 换 `redis.asyncio`/aioredis，设连接与命令超时，失败显式降级+metrics。
- P1 `Dockerfile`: 构建代理留在运行时 ENV。→ 构建结束清理代理 ENV，或仅 build 阶段临时变量。
- P1 `services.ingestion`: 单个 AsyncSession 贯穿 LLM/向量写入，无超时。→ 拆短事务、后台任务化、使用 asyncio.timeout/重试。
- P2 `middleware.audit`: 覆盖面窄（缺 admin/API Key/OpenAI 接口）。→ 按路由元数据扩展审计。
- P2 异常码不一致：部分路由直接字符串 detail。→ 统一 `{code, detail}` 响应包装。
- P2 `infra.bm25_store`: 内存实现无持久/重建，跨实例不一致。→ 引入持久化或启动重建。
- P1 日志上下文缺 tenant_id：未调用 `set_tenant_id`。→ 在认证依赖设置/清理 ContextVar。
- P1 SDK ACL 字段不匹配：`sdk/client.py` 仅支持 `acl` 字段，后端期望 `acl_users/roles/groups`。→ 调整 payload、补类型和超时重试。
- P1 前端持久化 API Key：localStorage 记录敏感 key。→ 换内存/sessionStorage，提供清除。

## Phase 3：工程化基线
- **质量链路**：`ruff format` + `ruff check --select ALL`、`mypy app/ sdk/`、`pytest tests/`（e2e 独立标记）。
- **CI**：流水线 lint→typecheck→unit→（可选 e2e）→docker build；上传覆盖率。
- **版本/发布**：SemVer；`CHANGELOG.md`+conventional commits；SDK 发布 PyPI，维护后端兼容矩阵。
- **安全**：依赖扫描 `pip-audit`/`safety`，密钥扫描 `gitleaks`；生产收敛 CORS/HTTPS，Redis 限流，API Key 生命周期管理。
- **性能**：压测 `/v1/retrieve` `/v1/rag` `/v1/knowledge-bases/*/documents`；SLO 建议 P95 检索 <800ms、RAG <1500ms；向量/LLM/embedding 设置超时+重试，热点缓存（query/embedding）。

## Phase 4：路线图
- **Quick Wins (1–2 天)**：向量检索下推 ACL Filter + 日志附带 tenant_id；验证受限文档过滤和正常 200。风险：Filter 误配；验收：ACL 过滤命中返回 403，日志/metrics 带 tenant_id。
- **Mid-term (1–2 周)**：异步限流器、审计覆盖 admin/API Key/OpenAI、统一错误码、SDK ACL 修复。风险：接口行为变化；验收：CI 新用例通过，审计覆盖 ≥90% 关键操作。
- **Strategic (1–2 月)**：摄取队列化+幂等、持久化 BM25 或 ES、Prometheus/Otel 全链路、移除镜像代理残留。风险：部署复杂度；验收：高并发摄取不阻塞、重启检索稳定、监控上线、镜像无敏感代理配置。

> 后续修复可按路线图分批推进，并在 PR 模板中勾选对应 Phase 项。 
