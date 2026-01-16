# RAGForge 测试目录

本目录包含 RAGForge 项目的所有测试文件。

## 测试统计

| 类型 | 数量 | 状态 |
|------|------|------|
| 单元测试 | 104 | ✅ 全部通过 |
| E2E 测试 | 5 | ⏭️ 需手动运行 |
| **总计** | **109** | - |

## 测试分类

### 单元测试

| 文件 | 功能 | 测试数 |
|------|------|--------|
| `test_acl_service.py` | ACL 权限服务（用户上下文、权限过滤、元数据构建） | 16 |
| `test_sdk_client.py` | SDK 客户端（KBServiceClient、ConversationAPI、RaptorAPI、ModelProviderAPI） | 12 |
| `test_pipeline_chunkers.py` | Pipeline 切分器（Simple、SlidingWindow、Recursive、Markdown、Code、ParentChild） | 30 |
| `test_config_validation.py` | 配置校验服务（KB 配置、Embedding 配置、切分器/检索器校验） | 20 |
| `test_embeddings.py` | Embedding 模块（哈希向量生成、维度校验、Unicode 支持） | 11 |
| `test_audit_service.py` | 审计日志服务（数据脱敏、敏感字段处理） | 15 |

### E2E 集成测试

| 文件 | 功能 | 环境变量 |
|------|------|----------|
| `test_e2e_health.py` | 健康检查接口测试 | `API_BASE` |
| `test_e2e_openai.py` | OpenAI 兼容接口测试 | `RUN_OPENAI_E2E`, `API_KEY` |
| `test_opensearch_e2e.py` | OpenSearch/ES 检索测试 | `RUN_ES_E2E` |

## 快速开始

### 运行所有单元测试

```bash
uv run pytest tests/ -v
```

### 运行指定测试文件

```bash
# ACL 服务测试
uv run pytest tests/test_acl_service.py -v

# Pipeline 切分器测试
uv run pytest tests/test_pipeline_chunkers.py -v

# SDK 客户端测试
uv run pytest tests/test_sdk_client.py -v
```

### 运行指定测试类或方法

```bash
# 运行指定测试类
uv run pytest tests/test_pipeline_chunkers.py::TestSimpleChunker -v

# 运行指定测试方法
uv run pytest tests/test_acl_service.py::TestUserContext::test_user_context_creation -v
```

## E2E 测试

E2E 测试需要先启动后端服务。

### 1. 启动服务

```bash
# 启动基础设施
docker compose up -d

# 启动 API 服务
uv run uvicorn app.main:app --port 8020
```

### 2. 运行 E2E 测试

```bash
# 健康检查测试
API_BASE="http://localhost:8020" uv run pytest tests/test_e2e_health.py -v

# OpenAI 兼容接口测试
RUN_OPENAI_E2E=1 API_KEY="your_api_key" API_BASE="http://localhost:8020" \
  uv run pytest tests/test_e2e_openai.py -v

# OpenSearch/ES 测试
RUN_ES_E2E=1 uv run pytest tests/test_opensearch_e2e.py -v
```

### 3. 完整端到端测试

```bash
API_KEY="your_api_key" API_BASE="http://localhost:8020" \
  uv run pytest test/test_live_e2e.py -v
```

## 测试覆盖

### ✅ 已覆盖模块

| 模块 | 覆盖内容 |
|------|----------|
| **ACL 权限服务** | UserContext、filter_results_by_acl、build_acl_filter_for_qdrant、build_acl_metadata_for_chunk |
| **SDK 客户端** | KBServiceClient、KBClient、ConversationAPI、RaptorAPI、ModelProviderAPI、rag_stream |
| **Pipeline 切分器** | SimpleChunker、SlidingWindowChunker、RecursiveChunker、MarkdownChunker、CodeChunker、ParentChildChunker |
| **配置校验** | validate_kb_config、Embedding 配置校验、存储类型校验 |
| **Embedding** | deterministic_hash_embed、维度处理、Unicode 支持 |
| **审计日志** | _sanitize_data、敏感字段脱敏 |

### ⬜ 待完善模块

- Pipeline 检索器（dense、hybrid、fusion、hyde 等）
- 文档入库服务
- RAG 生成服务
- API 路由层

## 编写测试指南

### 测试文件规范

1. 文件名以 `test_` 开头
2. 使用 pytest 框架
3. 测试类以 `Test` 开头
4. 测试方法以 `test_` 开头

### 测试模板

```python
"""
模块功能测试

测试 xxx 模块：
- 功能点 1
- 功能点 2
"""

import pytest


class TestFeatureName:
    """测试功能名称"""
    
    def test_basic_case(self):
        """测试基本场景"""
        # Arrange
        input_data = "test"
        
        # Act
        result = some_function(input_data)
        
        # Assert
        assert result == expected_value
    
    def test_edge_case(self):
        """测试边界条件"""
        pass
    
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """测试异步操作"""
        result = await async_function()
        assert result is not None
```

### 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """异步函数测试"""
    result = await some_async_function()
    assert result is not None
```

### E2E 测试标记

```python
import pytest

pytestmark = pytest.mark.e2e

def test_api_endpoint():
    """API 端点测试"""
    pass
```

## 常用命令

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行并显示覆盖率
uv run pytest tests/ -v --cov=app

# 只运行失败的测试
uv run pytest tests/ -v --lf

# 运行匹配关键字的测试
uv run pytest tests/ -v -k "chunker"

# 并行运行测试
uv run pytest tests/ -v -n auto
```
