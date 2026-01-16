# Scripts 运维脚本

本目录包含 RAGForge 的运维和管理脚本。

## 备份与恢复

| 脚本 | 说明 |
|------|------|
| `backup.sh` | 备份 PostgreSQL、Qdrant、Redis 和配置文件 |
| `restore.sh` | 从备份恢复数据 |

```bash
# 执行备份
./scripts/backup.sh

# 从指定日期恢复
./scripts/restore.sh 20260115_020000
```

## BM25 索引

| 脚本 | 说明 |
|------|------|
| `rebuild_bm25.py` | 从数据库重建 BM25 内存索引 |
| `migrate_bm25_to_es.py` | 将 BM25 数据迁移到 ES/OpenSearch |
| `manage_es_indices.py` | ES/OpenSearch 索引管理工具 |

```bash
# 重建 BM25 索引
uv run python scripts/rebuild_bm25.py --tenant TENANT_ID

# 迁移到 ES
uv run python scripts/migrate_bm25_to_es.py --tenant TENANT_ID --backend es

# 管理 ES 索引
uv run python scripts/manage_es_indices.py list
```

## Docker

| 脚本 | 说明 |
|------|------|
| `docker-entrypoint.sh` | Docker 容器启动脚本（Dockerfile 引用）|

## 调试

| 脚本 | 说明 |
|------|------|
| `diagnose_network.sh` | 网络连通性诊断 |

```bash
./scripts/diagnose_network.sh
```
