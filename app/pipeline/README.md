# Pipeline 模块开发指南

本文档详细介绍如何在 Self-RAG Pipeline 项目中添加新的 RAG 优化方法，以 **RAPTOR** 的完整添加过程为例进行逐步讲解。

---

## 1. 架构概述

### 1.1 Pipeline 模块结构

```
app/pipeline/
├── __init__.py          # 导出 operator_registry
├── base.py              # 基础协议定义
├── registry.py          # 算法注册表和装饰器
├── chunkers/            # 切分器实现
├── retrievers/          # 检索器实现
├── indexers/            # 索引器实现
├── query_transforms/    # 查询变换
├── enrichers/           # 文档增强
└── postprocessors/      # 后处理器
```

### 1.2 核心概念

| 概念 | 说明 | 接口 |
|------|------|------|
| **Chunker** | 文档切分器 | `BaseChunkerOperator.chunk()` (同步) |
| **Retriever** | 检索器 | `BaseRetrieverOperator.retrieve()` (异步) |
| **Indexer** | 索引构建器 | 自定义类，通常包含 `build_from_texts()` |
| **Registry** | 算法注册表 | `@register_operator(kind, name)` 装饰器 |

---

## 2. 开发流程总览

添加新的 RAG 优化方法需要以下步骤：

```
Step 1: 添加依赖 (pyproject.toml)
    ↓
Step 2: 同步依赖 (uv sync → uv.lock)
    ↓
Step 3: 实现索引器 (app/pipeline/indexers/xxx.py)
    ↓
Step 4: 实现检索器 (app/pipeline/retrievers/xxx.py)
    ↓
Step 5: 更新 API Schema (app/schemas/config.py)
    ↓
Step 6: 重建 Docker 镜像
    ↓
Step 7: 重启服务
    ↓
Step 8: 测试验证
    ↓
Step 9: 更新文档
```

---

## Step 1: 添加依赖

### 1.1 修改 pyproject.toml

**文件**: `pyproject.toml`

在 `[project].dependencies` 中添加新依赖，例如 RAPTOR 需要：

```toml
"llama-index-packs-raptor>=0.1.3"      # RAPTOR 核心包
"llama-index-llms-ollama>=0.1.0"       # Ollama LLM 支持
"llama-index-embeddings-ollama>=0.1.0" # Ollama Embedding 支持
```

### 1.2 注意事项

- 注意版本兼容性
- 某些包可能有隐式依赖，需要一并添加

---

## Step 2: 同步依赖并更新 uv.lock

### 2.1 本地同步

```bash
# 同步依赖（会自动更新 uv.lock）
uv sync

# 如果需要代理
export http_proxy="http://your-proxy:port"
export https_proxy="http://your-proxy:port"
uv sync
```

### 2.2 验证 uv.lock 更新

```bash
# 检查 uv.lock 是否有变更
git diff uv.lock

# 确认新包已添加
grep "llama-index-packs-raptor" uv.lock
```

### 2.3 提交 uv.lock

```bash
# uv.lock 必须提交到版本控制
git add pyproject.toml uv.lock
git commit -m "feat: add RAPTOR dependencies"
```

**重要**: `uv.lock` 锁定了所有依赖的精确版本，确保开发和生产环境一致。

---

## Step 3: 实现索引器

### 3.1 创建索引器文件

**文件**: `app/pipeline/indexers/xxx.py`

### 3.2 索引器设计要点

1. **依赖可选性**: 使用 `XXX_AVAILABLE` 标志处理依赖缺失
2. **数据结构**: 定义清晰的数据类（如 `RaptorNode`, `RaptorIndexResult`）
3. **错误处理**: 所有外部调用都有异常处理
4. **日志记录**: 关键步骤都有日志输出
5. **工厂函数**: 提供 `create_xxx_from_config()` 简化使用

### 3.3 在 __init__.py 中导出

**文件**: `app/pipeline/indexers/__init__.py`

添加导入和 `__all__` 导出。

---

## Step 4: 实现检索器

### 4.1 创建检索器文件

**文件**: `app/pipeline/retrievers/xxx.py`

### 4.2 检索器设计要点

1. **装饰器注册**: `@register_operator("retriever", "xxx")` 自动注册到注册表
2. **类属性**: 必须定义 `name` 和 `kind` 属性
3. **异步方法**: `retrieve()` 方法必须是异步的
4. **回退机制**: 当特殊索引不可用时，回退到基础检索器
5. **结果格式**: 返回 `list[dict]`，包含 `chunk_id`, `text`, `score`, `source` 等字段

### 4.3 在 __init__.py 中导入

**文件**: `app/pipeline/retrievers/__init__.py`

添加导入和 `__all__` 导出。

---

## Step 5: 更新 API Schema

### 5.1 添加到 RetrieverName 类型

**文件**: `app/schemas/config.py`

在 `RetrieverName` Literal 类型中添加新的检索器名称：

```python
RetrieverName = Literal[
    "dense",
    "bm25",
    # ... 现有检索器 ...
    "xxx",  # ← 新增
]
```

### 5.2 为什么需要这一步？

Pydantic 使用 `Literal` 类型进行请求验证。如果不添加，API 调用时会返回验证错误。

---

## Step 6: 重建 Docker 镜像

代码修改后，需要重建 Docker 镜像以使更改生效。

### 6.1 重建镜像

```bash
# 方式 1: 使用 docker compose（推荐）
docker compose build api

# 方式 2: 使用代理加速（网络不好时）
docker compose build api --build-arg HTTP_PROXY=http://your-proxy:port

# 方式 3: 使用宿主机网络构建（最快）
docker build --network=host -t self_rag_pipeline-api .
```

### 6.2 验证镜像

```bash
# 检查镜像是否更新
docker images | grep self_rag_pipeline

# 验证依赖是否安装
docker run --rm self_rag_pipeline-api uv pip list | grep raptor
```

---

## Step 7: 重启服务

### 7.1 重启容器

```bash
# 方式 1: 重建并启动（最彻底）
docker compose up -d --build api

# 方式 2: 仅重启（镜像已更新时）
docker compose restart api

# 方式 3: 停止后启动
docker compose down
docker compose up -d
```

### 7.2 验证服务启动

```bash
# 查看日志
docker compose logs -f api

# 检查服务状态
docker compose ps

# 测试健康检查
curl http://localhost:8020/health
```

### 7.3 验证新功能可用

```bash
# 进入容器测试
docker compose exec api uv run python -c "
from app.pipeline.indexers.raptor import RAPTOR_AVAILABLE
print(f'RAPTOR Available: {RAPTOR_AVAILABLE}')
"
```

---

## Step 8: 测试验证

### 8.1 容器内测试

```bash
docker compose exec api uv run python -c "
from app.pipeline.indexers.raptor import create_raptor_indexer_from_config

indexer = create_raptor_indexer_from_config()
if indexer:
    result = indexer.build_from_texts(['测试文本1', '测试文本2'])
    print(f'节点数: {result.total_nodes}')
"
```

### 8.2 API 测试

```bash
curl -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["kb-id"],
    "retriever_override": {"name": "raptor"}
  }'
```
> 注意：检索会先完成向量/BM25 等检索，然后再做 ACL 权限过滤。如果命中了内容但因敏感度/ACL 被全部过滤，接口会返回 403，提示没有权限访问这些结果。

---

## Step 9: 更新文档

### 9.1 需要更新的文档

| 文档 | 更新内容 |
|------|----------|
| `AGENTS.md` | 检索器列表添加新检索器 |
| `docs/测试记录.md` | 添加测试结果 |
| `app/pipeline/README.md` | 更新本文档 |

---

## 完整文件清单

添加新优化方法需要修改/创建的文件：

| 文件 | 操作 | 说明 |
|------|------|------|
| `pyproject.toml` | 修改 | 添加依赖 |
| `uv.lock` | 自动更新 | 运行 `uv sync` 后自动更新 |
| `app/pipeline/indexers/xxx.py` | 创建 | 索引器实现 |
| `app/pipeline/indexers/__init__.py` | 修改 | 导出索引器 |
| `app/pipeline/retrievers/xxx.py` | 创建 | 检索器实现 |
| `app/pipeline/retrievers/__init__.py` | 修改 | 导出检索器 |
| `app/schemas/config.py` | 修改 | 添加 RetrieverName |
| `AGENTS.md` | 修改 | 更新文档 |
| `docs/测试记录.md` | 修改 | 添加测试结果 |

---

## 常见问题

### Q1: 依赖导入失败？

**症状**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
1. 检查 `pyproject.toml` 是否添加了依赖
2. 运行 `uv sync` 同步依赖
3. 重建 Docker 镜像: `docker compose build api`
4. 重启服务: `docker compose restart api`

### Q2: 检索器未注册？

**症状**: `KeyError: 'xxx' not found in retriever registry`

**解决**:
1. 检查 `@register_operator` 装饰器是否正确
2. 检查 `retrievers/__init__.py` 是否导入了新模块
3. 确认模块没有语法错误导致导入失败

### Q3: API 验证失败？

**症状**: `literal_error: Input should be 'dense', 'bm25', ...`

**解决**:
1. 检查 `app/schemas/config.py` 中 `RetrieverName` 是否添加了新名称
2. 重启 API 服务使更改生效

### Q4: Docker 镜像没有更新？

**症状**: 代码修改后功能没有生效

**解决**:
```bash
# 强制重建
docker compose build --no-cache api

# 或者删除旧镜像后重建
docker rmi self_rag_pipeline-api
docker compose build api
```

### Q5: uv.lock 冲突？

**症状**: 合并代码时 uv.lock 有冲突

**解决**:
```bash
# 接受当前版本的 pyproject.toml 后重新生成
git checkout --ours pyproject.toml
uv sync
git add uv.lock
```

---

## 参考资料

- [RAPTOR 论文](https://arxiv.org/abs/2401.18059)
- [LlamaIndex RAPTOR Pack](https://docs.llamaindex.ai/en/stable/examples/retrievers/raptor/)
- [项目 AGENTS.md](/AGENTS.md)
