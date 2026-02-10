# RAGForge 架构说明

本文概览系统的核心组件、关键流程以及多租户/权限控制设计，便于新成员快速理解代码与运行方式。

## 组件总览
- **API 层**：`app/main.py` + `app/api/routes/*`，FastAPI 提供租户、KB、文档、检索、RAG、OpenAI 兼容接口。
- **服务层**：`app/services/*`，封装业务逻辑：摄取 (`ingestion.py`)、检索 (`query.py`)、RAG (`rag.py`)、ACL (`acl.py`) 等。
- **Pipeline/算法层**：`app/pipeline/*`，通过 `operator_registry` 注册可插拔的 chunkers/retrievers/query transforms/enrichers/postprocessors/indexers。
- **基础设施层**：`app/infra/*`，LLM/Embedding/Rerank 客户端、Qdrant 向量库、BM25 内存库、LlamaIndex 适配、日志与指标。
- **数据访问层**：`app/db/*` + `app/models/*` + `alembic/versions`，SQLAlchemy ORM 模型与 Alembic 迁移。
- **SDK**：`sdk/`，同步 Python 客户端封装全部 API。
- **前端**：`frontend/`，Next.js 管理/演示界面。
- **容器化**：`Dockerfile`（uv + FastAPI）与 `docker-compose.yml`（API + Postgres + Qdrant）。

## 运行拓扑
- **数据库**：PostgreSQL（元数据、ACL、审计），连接池在 `app/db/session.py`。
- **向量库**：Qdrant，支持 `partition`（共享集合按 `tenant_id` 过滤）与 `collection`（每租户独立集合）模式，默认 `auto`。
- **稀疏检索**：`bm25_store.py` 支持内存 BM25（默认，仅单实例）和 ES/OpenSearch 后端（配置 `bm25_backend=es`，使用 `ES_HOSTS` 等），也可用 `bm25_enabled=False` 关闭。
- **模型供应商**：Ollama/OpenAI/Gemini/Qwen/DeepSeek/智谱/SiliconFlow 等，配置在 `app/config.py`。
- **可观测性**：结构化日志 (`app/infra/logging.py`)、调用/检索指标 (`app/infra/metrics.py`)、`/health` `/ready` `/metrics` 端点，审计中间件 (`app/middleware/audit.py`)。

## 关键流程
### 文档摄取（/v1/knowledge-bases/{kb_id}/documents）
1. **认证/租户检查**：`get_api_key_context` 校验 API Key、限流、租户状态；`ensure_kb_belongs_to_tenant` 确认 KB 归属。
2. **切分**：`app/services/ingestion.py` 解析 KB 配置，`operator_registry` 取 chunker（如 `sliding_window`/`parent_child`），生成 `Chunk` 记录。
3. **ACL 元数据**：从 `Document` 的 `sensitivity_level/acl_*` 生成 chunk payload（`build_acl_metadata_for_chunk`）。
4. **向量化与写入**：调用 `app/infra/vector_store.py::upsert_chunks`（Qdrant，按租户隔离策略选择 collection/partition）；BM25 内存索引同步更新；可选 RAPTOR/LlamaIndex。
5. **状态与日志**：写入 `processing_log/processing_status`，失败时记录重试信息。

### 检索（/v1/retrieve）
1. **认证/范围**：API Key 验证 → scope_kb_ids 白名单校验 → KB 归属校验。
2. **检索器解析**：`retrieve_chunks` 根据 KB 配置或 override 选择 retriever（dense/hybrid/hyde/multi_query/fusion/self_query...），可透传 embedding/rerank override。
3. **向量/稀疏检索**：调用 retriever → Qdrant `search`（按 tenant/kb 过滤）+ 可选 BM25/融合/LLM 扩展。
4. **后处理**：Context Window、父子块补充、Rerank；ACL 二次过滤（`filter_results_by_acl`）。若有命中但被 ACL 清空，返回 403 `NO_PERMISSION`。
5. **响应**：包装 `ModelInfo`（embedding/llm/rerank/retriever）和命中列表。

### RAG（/v1/rag, /v1/chat/completions）
1. **检索**：复用 `retrieve_chunks`（含 ACL）。
2. **Prompt 组装**：`app/services/rag.py` 将 chunk 文本拼接上下文模板。
3. **LLM 生成**：`chat_completion` 或 `chat_completion_with_config` 调用配置的 LLM；返回 answer + sources + model 元信息。

## 多租户与权限
- **身份与限流**：API Key 存储哈希，附带 `role` + `scope_kb_ids` + `identity(user/roles/groups/clearance)`；`get_api_key_context` 统一校验 + 滑动窗口限流。
- **租户隔离**：关系型数据通过 `tenant_id` 外键与索引；向量库通过 collection/partition + `kb_id`/`tenant_id` payload 过滤。
- **ACL/Security Trimming**：文档存储 `sensitivity_level` 与 ACL 列，摄取时写入 chunk payload；检索后在应用层再次过滤以避免越权。
- **审计**：`AuditLogMiddleware` 捕获检索、RAG、KB/文档写操作，异步写入审计表。

## 扩展点
- **Chunkers**：`app/pipeline/chunkers/*` 注册到 `operator_registry`，支持 simple/sliding/recursive/markdown/code/parent_child/llama_*。
- **Retrievers**：`app/pipeline/retrievers/*`，支持 dense/bm25/hybrid/fusion/hyde/multi_query/self_query/ensemble/llama_*。
- **Query transforms / Enrichers / Postprocessors / Indexers**：分别位于对应子目录，可通过注册表添加新实现。

## 数据模型速览
- **Tenant, APIKey, KnowledgeBase, Document, Chunk, Conversation**, **AuditLog**, **UsageLog**, **RaptorNode**, **SystemConfig** 等，详见 `app/models/` 与 `alembic/versions`。

## 部署与运行
- 本地：`uv sync` → `docker compose up -d db qdrant` → `uv run alembic upgrade head` → `uv run uvicorn app.main:app --reload --port 8020`。
- Docker Compose：`docker compose up -d`，容器内运行 `alembic upgrade head`，API 暴露 8020。
- 健康与监控：`/health`（存活）、`/ready`（依赖检查）、`/metrics`（运行时与调用统计）。

## 运维提示
- BM25：默认启用内存索引，可通过 `bm25_enabled=False` 关闭；重启后可用 `scripts/rebuild_bm25.py` 从数据库重建（适合单实例/小规模）。
- Docker 代理：构建期可配置 `BUILD_HTTP_PROXY`，镜像运行时已清空 `http_proxy/https_proxy` 以避免意外走代理。
