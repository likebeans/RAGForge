# 架构决策记录 (ADRs)

本文档记录 Self-RAG Pipeline 项目的重要架构和工程决策，便于团队共享背景与权衡。

## 决策模板

每个决策记录包含以下部分：
- **Context**：业务/技术背景、约束、目标
- **Decision**：选项、最终选择与理由
- **Status**：Proposed / Accepted / Superseded
- **Consequences**：正负面影响、后续工作
- **References**：相关 Issue/PR/文档

## ADR 1：向量库多租户隔离策略

- **Context**：Qdrant 需要在隔离与资源利用之间平衡；租户数据量差异大。
- **Decision**：默认 `auto`：<阈值使用共享 partition（同 collection，`tenant_id` 过滤），超阈值或手工指定使用 per-tenant collection。集合名前缀来自 `qdrant_collection_prefix`。
- **Status**：Accepted
- **Consequences**：
  - 小租户资源开销低；大租户避免热点干扰
  - 需要提供迁移工具在 partition ↔ collection 之间切换
  - Collection 按维度区分，embedding 变更需校验
- **References**: `app/infra/vector_store.py`

## ADR 2：ACL 安全修整（Security Trimming）

- **Context**：文档支持敏感度 + ACL 白名单；需要在检索链路防止越权。
- **Decision**：摄取时把 `sensitivity_level/acl_*` 写入 chunk payload；检索阶段先向量库过滤（后续将下推至 Qdrant Filter），再在应用层二次过滤（`filter_results_by_acl`），若命中被完全过滤返回 403 `NO_PERMISSION`。
- **Status**：Accepted（需加强向量库下推与日志覆盖）
- **Consequences**：
  - 双层过滤提高安全冗余
  - 需要在 Qdrant 搜索请求中附加 ACL Filter 以降低泄露面与提高性能
  - ACL 字段变更需要触发重新索引
- **References**: `app/services/acl.py`, `app/services/query.py`, `app/infra/vector_store.py`

## ADR 3：摄取执行模型

- **Context**：摄取包含切分/LLM/向量化，耗时长且易受外部依赖影响。
- **Decision**：当前在 API 请求内同步执行，使用 `processing_status`/`processing_log` 反馈进度，失败可重试；保留未来切换到任务队列（Celery/RQ/Arq）与幂等重试的演进路径。
- **Status**：Proposed（建议落地队列化与事务围栏）
- **Consequences**：
  - 简化依赖，便于本地/小规模场景
  - 在高并发或 LLM 慢速时占用 DB 连接与 worker，需队列化+分布式锁
  - 需要幂等键（doc_id）与可恢复的部分进度记录
- **References**: `app/services/ingestion.py`

## ADR 4：可插拔算法框架设计

- **Context**：需要支持多种切分、检索、增强策略，且能够灵活组合和扩展。
- **Decision**：采用基于注册表的插件架构，通过 `operator_registry` 统一管理算法组件，支持运行时动态注册和发现。
- **Status**：Accepted
- **Consequences**：
  - 算法组件解耦，易于测试和维护
  - 支持第三方插件扩展
  - 配置驱动的算法选择，无需修改代码
  - 需要维护统一的接口规范
- **References**: `app/pipeline/registry.py`, `app/pipeline/base.py`

## ADR 5：异步优先的 I/O 模型

- **Context**：系统涉及大量 I/O 操作（数据库、向量库、LLM API），需要高并发处理能力。
- **Decision**：全面采用 async/await 模式，所有 I/O 操作异步化，使用异步数据库连接池和向量库客户端。
- **Status**：Accepted
- **Consequences**：
  - 提高并发处理能力和资源利用率
  - 避免阻塞事件循环导致的性能问题
  - 代码复杂度增加，需要注意异步上下文管理
  - 第三方库需要支持异步操作
- **References**: `app/db/session.py`, `app/infra/vector_store.py`

## ADR 6：模型配置动态化

- **Context**：不同租户和场景需要使用不同的 LLM/Embedding 模型，环境变量配置不够灵活。
- **Decision**：实现多层级配置系统（请求级 > 知识库级 > 租户级 > 系统级 > 环境变量），支持运行时动态切换模型。
- **Status**：Accepted
- **Consequences**：
  - 提高系统灵活性，支持多租户差异化需求
  - 无需重启服务即可切换模型配置
  - 配置管理复杂度增加
  - 需要处理配置优先级和兼容性问题
- **References**: `app/services/model_config.py`, `app/models/system_config.py`

## ADR 7：OpenAI 兼容接口设计

- **Context**：为了降低用户迁移成本，需要提供与 OpenAI API 兼容的接口。
- **Decision**：实现完整的 OpenAI 兼容 API（Chat Completions、Embeddings），同时扩展支持 RAG 特有参数（如 `knowledge_base_ids`）。
- **Status**：Accepted
- **Consequences**：
  - 用户可以无缝迁移现有的 OpenAI 客户端代码
  - 降低学习成本和集成难度
  - 需要维护与 OpenAI API 的兼容性
  - 扩展参数可能与标准不完全一致
- **References**: `app/api/routes/openai_compat.py`, `sdk/`

## ADR 8：安全优先的权限控制

- **Context**：多租户环境下需要严格的权限控制和数据隔离。
- **Decision**：实现多层次安全控制：API Key 角色权限 + 租户隔离 + 文档级 ACL + Security Trimming。
- **Status**：Accepted
- **Consequences**：
  - 提供企业级安全保障
  - 支持细粒度权限控制
  - 安全检查增加系统复杂度和性能开销
  - 需要完善的审计日志和监控
- **References**: `app/auth/`, `app/services/acl.py`, `app/middleware/audit.py`