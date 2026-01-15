# 稀疏检索（BM25）迁移到 Elasticsearch/OpenSearch

## 背景
- 旧实现：内存 BM25（单实例，重启丢数据，不支持多副本）。
- 目标：使用 ES/OpenSearch 作为稀疏检索后端，支持多租户、持久化与横向扩展，同时保留向后兼容与快速回滚。

## 配置项
在 `.env` 或环境变量中设置：
- `bm25_enabled`：`true/false`，是否启用稀疏检索（默认 `true`）。
- `bm25_backend`：`memory`（默认）| `es`，选择后端。
- `ES_HOSTS`：必填，逗号分隔，例如 `http://localhost:9200` 或 OpenSearch 端点。
- `ES_USERNAME` / `ES_PASSWORD`：可选，HTTP 基本认证。
- `ES_INDEX_PREFIX`：索引前缀，默认 `kb_`。
- `ES_INDEX_MODE`：`shared`（单索引，按 `tenant_id/kb_id` 过滤）或 `per_kb`（每个 KB 一个索引，隔离强但索引数多），默认 `shared`。
- `ES_REQUEST_TIMEOUT`：请求超时（秒），默认 `10`。
- `ES_BULK_BATCH_SIZE`：bulk 写入批大小，默认 `500`。

示例：
```
bm25_enabled=true
bm25_backend=es
ES_HOSTS=http://localhost:9200
ES_USERNAME=admin
ES_PASSWORD=admin
ES_INDEX_PREFIX=kb_
ES_INDEX_MODE=shared
ES_REQUEST_TIMEOUT=10
ES_BULK_BATCH_SIZE=500
es_analyzer=standard
es_refresh=false
```

## 索引策略
- 索引名：`{ES_INDEX_PREFIX}shared`（shared 模式）或 `{prefix}{tenant_id}_{kb_id}`（per_kb）。
- 字段：`text`、`metadata`、`tenant_id`、`kb_id`、`doc_id`、`chunk_id`、`created_at`。
- 过滤：查询时带 `tenant_id/kb_id` filter，避免跨租户/跨 KB 泄漏。
- ACL：仍由上层 ACL trimming 执行（向量检索一致），如需下推可后续扩展。

## 迁移方案
### 方案 A：冷迁移（简单可靠）
1. 配置 ES 并确认健康。
2. 暂停内存 BM25 写入（`bm25_enabled=false` 或临时停止服务）。
3. 运行迁移脚本，将数据库中的 chunk 写入 ES：
   ```
   uv run python scripts/migrate_bm25_to_es.py --tenant <tenant_id> [--kb <kb_id>] --backend es
   ```
4. 切换配置 `bm25_enabled=true` `bm25_backend=es`，重启服务。
5. 验证检索与 ACL；如异常，回滚到 `bm25_backend=memory`。

### 方案 B：双写灰度（推荐渐进）
1. 保持 `bm25_backend=memory`，开启临时双写脚本：
   ```
   uv run python scripts/migrate_bm25_to_es.py --tenant <tenant_id> --watch --backend es
   ```
   该脚本读取 DB 的 chunks 持续写入 ES（简易“追赶”）。
2. 验证 ES 检索效果（可在灰度环境将 `bm25_backend=es`）。
3. 切换线上 `bm25_backend=es`，观察一段时间。
4. 回滚：切回 `bm25_backend=memory`（内存已有数据则继续使用；如需同步 DB→内存可用 `scripts/rebuild_bm25.py`）。

### 回滚
- 将配置改回 `bm25_backend=memory`，必要时关闭 bm25（`bm25_enabled=false`）。
- 若需要恢复内存索引：`uv run python scripts/rebuild_bm25.py --tenant <tenant_id> [--kb <kb_id>]`。

## 验收标准
- 切换到 ES 后，`/v1/retrieve` 和 `/v1/rag` 能正常返回，入库/删除同步到 ES。
- 多租户隔离：tenant A 的数据在 ES 检索不会返回给 tenant B。
- 日志/指标：检索日志包含 `retriever=bm25_es`、`backend=es`、latency 信息。

## 风险与建议
- **映射/分词**：当前使用默认 analyzer，中文可根据需要定制（IK/Synonym）。变更 analyzer 需重建索引。
 - **索引模式**：`shared` 索引少但查询需 filter；`per_kb` 隔离强但索引爆炸，需监控索引数。建议设置索引数阈值告警（如 >500 报警），定期清理废弃索引。
- **写入与刷新**：bulk 默认 `refresh` 延后，若需实时可在写入后刷新但会降低性能。
- **权限**：ES 账号应最小权限；OpenSearch 建议开启认证/签名。
- **超时与重试**：已配置请求超时；如果 ES 不可达，检索会降级到无结果（不回退 memory）；可通过观测告警。
- **容量与生命周期**：生产建议配置 ILM/ISM，控制 shard/replica，定期监控磁盘与查询慢日志。
- **回滚**：保留内存 BM25 配置可快速切换；大规模数据回滚需预先准备内存或其他稀疏后端。
