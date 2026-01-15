# 测试指南

本文档记录 Self-RAG Pipeline 系统的测试策略、测试环境配置和各功能模块的测试方法。

## 测试环境配置

### 基础环境

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **Python 版本** | 3.11+ | 推荐使用最新稳定版 |
| **API 服务端口** | 8020 | 本地开发端口 |
| **PostgreSQL 端口** | 5435 (宿主机) / 5432 (容器内) | 数据库服务 |
| **Qdrant 端口** | 6333 | 向量数据库服务 |
| **Redis 端口** | 6379 | 缓存和限流服务 |

### 模型配置

推荐使用 Ollama 进行本地测试：

```bash
# Embedding 模型
export EMBEDDING_PROVIDER=ollama
export EMBEDDING_MODEL="bge-m3"
export EMBEDDING_DIM=1024

# LLM 模型
export LLM_PROVIDER=ollama
export LLM_MODEL="qwen3:14b"

# Ollama 服务地址（使用固定 IP，本地和 Docker 都能访问）
export OLLAMA_BASE_URL="http://192.168.1.235:11434"

# OpenAI 兼容接口（用于 HyDE 等功能）
export OPENAI_API_BASE="http://192.168.1.235:11434/v1"
export OPENAI_API_KEY="ollama"  # 任意非空值
```

### 测试数据库

使用独立的测试数据库避免污染开发数据：

```bash
# 测试数据库配置
export TEST_DATABASE_URL="postgresql+asyncpg://kb:kb@localhost:5435/kb_test"

# 创建测试数据库
createdb -h localhost -p 5435 -U kb kb_test
```

## 测试分类

### 单元测试

测试单个函数或类的功能，使用 mock 隔离外部依赖：

```bash
# 运行所有单元测试
uv run pytest tests/unit/ -v

# 运行特定模块的测试
uv run pytest tests/unit/test_chunkers.py -v

# 运行带覆盖率的测试
uv run pytest tests/unit/ --cov=app --cov-report=html
```

### 集成测试

测试多个组件的协作，使用真实的数据库和服务：

```bash
# 运行集成测试
uv run pytest tests/integration/ -v

# 测试数据库操作
uv run pytest tests/integration/test_database.py -v

# 测试 API 路由
uv run pytest tests/integration/test_api.py -v
```

### 端到端测试

测试完整的 API 流程，需要运行中的服务：

```bash
# 启动测试环境
docker compose up -d db qdrant redis
uv run uvicorn app.main:app --port 8020 &

# 运行端到端测试
API_BASE=http://localhost:8020 API_KEY=your_test_key \
uv run pytest test/test_live_e2e.py -v

# 运行性能测试
uv run pytest test/test_performance.py -v
```

## 功能测试

### 基础功能测试

#### 健康检查

```bash
# 存活检查
curl -s -w "\nHTTP: %{http_code}\n" http://localhost:8020/health

# 就绪检查（包含依赖服务状态）
curl -s http://localhost:8020/ready | python3 -m json.tool

# 系统指标
curl -s http://localhost:8020/metrics | python3 -m json.tool
```

#### 认证测试

```bash
# 有效 API Key
curl -s "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"

# 无效 API Key（期望 401）
curl -s -w "\nHTTP: %{http_code}\n" \
  -H "Authorization: Bearer invalid_key" \
  "$API_BASE/v1/knowledge-bases"

# 缺少认证头（期望 401）
curl -s -w "\nHTTP: %{http_code}\n" \
  "$API_BASE/v1/knowledge-bases"
```

#### 知识库管理

```bash
# 创建知识库
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试知识库", "description": "用于测试的知识库"}'

# 列出知识库
curl -s "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"

# 获取知识库详情
curl -s "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY"

# 更新知识库配置
curl -s -X PATCH "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "更新后的描述"}'

# 删除知识库
curl -s -X DELETE "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY"
```

#### 文档管理

```bash
# 上传文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试文档",
    "content": "这是一个测试文档的内容..."
  }'

# 批量上传文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents/batch" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"title": "文档1", "content": "内容1"},
      {"title": "文档2", "content": "内容2"}
    ]
  }'

# 文件上传
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@test.md" \
  -F "title=上传的文档"

# URL 拉取
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "GitHub README",
    "source_url": "https://raw.githubusercontent.com/user/repo/main/README.md"
  }'

# 列出文档
curl -s "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY"

# 获取文档详情
curl -s "$API_BASE/v1/documents/$DOC_ID" \
  -H "Authorization: Bearer $API_KEY"

# 删除文档
curl -s -X DELETE "$API_BASE/v1/documents/$DOC_ID" \
  -H "Authorization: Bearer $API_KEY"
```

### 切分器测试

#### 基础切分器

```bash
# simple 切分器（按段落）
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Simple切分测试",
    "config": {
      "ingestion": {
        "chunker": {"name": "simple"}
      }
    }
  }'

# sliding_window 切分器
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SlidingWindow切分测试",
    "config": {
      "ingestion": {
        "chunker": {
          "name": "sliding_window",
          "params": {"window": 512, "overlap": 100}
        }
      }
    }
  }'

# recursive 切分器（推荐用于通用文档）
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Recursive切分测试",
    "config": {
      "ingestion": {
        "chunker": {
          "name": "recursive",
          "params": {"chunk_size": 1024, "chunk_overlap": 256}
        }
      }
    }
  }'
```

#### 高级切分器

```bash
# markdown 切分器（按标题层级）
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Markdown切分测试",
    "config": {
      "ingestion": {
        "chunker": {"name": "markdown"}
      }
    }
  }'

# code 切分器（按语法结构）
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code切分测试",
    "config": {
      "ingestion": {
        "chunker": {
          "name": "code",
          "params": {"language": "python"}
        }
      }
    }
  }'

# parent_child 切分器（父子分块）
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ParentChild切分测试",
    "config": {
      "ingestion": {
        "chunker": {
          "name": "parent_child",
          "params": {"parent_chars": 2000, "child_chars": 500}
        }
      }
    }
  }'
```

### 检索器测试

#### 基础检索器

```bash
# dense 检索器（稠密向量检索）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {"name": "dense"}
  }'

# bm25 检索器（关键词检索）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {"name": "bm25"}
  }'

# hybrid 检索器（混合检索）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {"name": "hybrid"}
  }'
```

#### 高级检索器

```bash
# fusion 检索器（RRF 融合）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {
      "name": "fusion",
      "params": {"mode": "rrf", "rerank": true}
    }
  }'

# hyde 检索器（假设文档嵌入）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {"name": "hyde"}
  }'

# multi_query 检索器（多查询扩展）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {
      "name": "multi_query",
      "params": {"num_queries": 3}
    }
  }'

# parent_document 检索器（需要 parent_child 切分器）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {"name": "parent_document"}
  }'

# raptor 检索器（多层次索引）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "retriever_override": {
      "name": "raptor",
      "params": {"mode": "collapsed"}
    }
  }'
```

### 权限系统测试

#### 多租户隔离

```bash
# 创建两个测试租户
TENANT_A=$(curl -s -X POST "$API_BASE/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "tenant-a"}')

TENANT_B=$(curl -s -X POST "$API_BASE/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "tenant-b"}')

# 提取 API Keys
API_KEY_A=$(echo $TENANT_A | jq -r '.initial_api_key')
API_KEY_B=$(echo $TENANT_B | jq -r '.initial_api_key')

# 租户 A 创建知识库
KB_A=$(curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY_A" \
  -H "Content-Type: application/json" \
  -d '{"name": "租户A的知识库"}')

KB_A_ID=$(echo $KB_A | jq -r '.id')

# 租户 B 尝试访问租户 A 的知识库（应该返回 404）
curl -s -w "\nHTTP: %{http_code}\n" \
  "$API_BASE/v1/knowledge-bases/$KB_A_ID" \
  -H "Authorization: Bearer $API_KEY_B"
```

#### 角色权限测试

```bash
# 创建不同角色的 API Key
READ_KEY=$(curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "read-only", "role": "read"}' | jq -r '.api_key')

WRITE_KEY=$(curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "write-access", "role": "write"}' | jq -r '.api_key')

# read 角色尝试创建知识库（应该返回 403）
curl -s -w "\nHTTP: %{http_code}\n" \
  -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试KB"}'

# write 角色创建知识库（应该成功）
curl -s -w "\nHTTP: %{http_code}\n" \
  -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $WRITE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试KB"}'

# read 角色尝试管理 API Key（应该返回 403）
curl -s -w "\nHTTP: %{http_code}\n" \
  -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "hack-attempt", "role": "admin"}'
```

#### ACL 权限测试

```bash
# 创建带身份信息的 API Key
SALES_KEY=$(curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sales-user",
    "role": "read",
    "identity": {
      "user_id": "sales001",
      "roles": ["sales"],
      "groups": ["dept_sales"]
    }
  }' | jq -r '.api_key')

# 上传受限文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "销售机密文档",
    "content": "这是销售部门的机密信息...",
    "sensitivity_level": "restricted",
    "acl_roles": ["sales", "manager"]
  }'

# 无权限用户检索（应该看不到受限文档）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "销售机密",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 10
  }'

# 有权限用户检索（应该能看到受限文档）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $SALES_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "销售机密",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 10
  }'
```

### 性能测试

#### 批量上传测试

```bash
# 创建测试脚本
cat > batch_upload_test.sh << 'EOF'
#!/bin/bash
API_BASE="http://localhost:8020"
API_KEY="your_api_key"
KB_ID="your_kb_id"

echo "开始批量上传测试..."
start_time=$(date +%s)

for i in {1..20}; do
  echo "上传文档 $i..."
  curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"测试文档$i\", \"content\": \"这是第$i个测试文档的内容...\"}" \
    > /dev/null
done

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "批量上传完成，总耗时: ${duration}秒"
echo "平均每文档: $((duration * 1000 / 20))ms"
EOF

chmod +x batch_upload_test.sh
./batch_upload_test.sh
```

#### 并发检索测试

```bash
# 创建并发测试脚本
cat > concurrent_test.sh << 'EOF'
#!/bin/bash
API_BASE="http://localhost:8020"
API_KEY="your_api_key"
KB_ID="your_kb_id"

echo "开始并发检索测试..."

# 并发执行 10 个检索请求
for i in {1..10}; do
  {
    start=$(date +%s.%3N)
    curl -s -X POST "$API_BASE/v1/retrieve" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"query\": \"测试查询$i\", \"knowledge_base_ids\": [\"$KB_ID\"], \"top_k\": 5}" \
      > /dev/null
    end=$(date +%s.%3N)
    duration=$(echo "$end - $start" | bc)
    echo "请求$i 耗时: ${duration}s"
  } &
done

wait
echo "并发检索测试完成"
EOF

chmod +x concurrent_test.sh
./concurrent_test.sh
```

## 测试数据管理

### 测试数据准备

```python
# tests/conftest.py
import pytest
from app.tests.utils import create_test_tenant, create_test_kb

@pytest.fixture
async def test_tenant():
    """创建测试租户"""
    tenant = await create_test_tenant("test-tenant")
    yield tenant
    # 清理测试数据
    await cleanup_tenant(tenant.id)

@pytest.fixture
async def test_kb(test_tenant):
    """创建测试知识库"""
    kb = await create_test_kb(test_tenant.api_key, "test-kb")
    yield kb
    # 知识库会随租户一起清理

@pytest.fixture
def sample_documents():
    """提供测试文档数据"""
    return [
        {
            "title": "Python 基础教程",
            "content": "Python 是一种高级编程语言..."
        },
        {
            "title": "机器学习入门",
            "content": "机器学习是人工智能的一个分支..."
        }
    ]
```

### 测试数据清理

```python
# tests/utils.py
async def cleanup_tenant(tenant_id: str):
    """清理测试租户及其所有数据"""
    async with get_db_session() as session:
        # 删除文档和 chunks
        await session.execute(
            delete(Chunk).where(Chunk.tenant_id == tenant_id)
        )
        await session.execute(
            delete(Document).where(Document.tenant_id == tenant_id)
        )
        
        # 删除知识库
        await session.execute(
            delete(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id)
        )
        
        # 删除 API Keys
        await session.execute(
            delete(APIKey).where(APIKey.tenant_id == tenant_id)
        )
        
        # 删除租户
        await session.execute(
            delete(Tenant).where(Tenant.id == tenant_id)
        )
        
        await session.commit()
    
    # 清理向量数据库
    await cleanup_vector_store(tenant_id)
```

## 自动化测试

### GitHub Actions 配置

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: kb
          POSTGRES_USER: kb
          POSTGRES_DB: kb_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Install uv
      uses: astral-sh/setup-uv@v1
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.11
    
    - name: Install dependencies
      run: uv sync
    
    - name: Run linting
      run: |
        uv run ruff check .
        uv run ruff format --check .
        uv run mypy app/
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql+asyncpg://kb:kb@localhost:5432/kb_test
        QDRANT_URL: http://localhost:6333
        REDIS_URL: redis://localhost:6379
      run: |
        uv run alembic upgrade head
        uv run pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 本地测试脚本

```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "🧪 运行 Self-RAG Pipeline 测试套件"

# 检查依赖服务
echo "📋 检查依赖服务..."
if ! curl -s http://localhost:5435 > /dev/null; then
    echo "❌ PostgreSQL 未启动，请运行: docker compose up -d db"
    exit 1
fi

if ! curl -s http://localhost:6333/health > /dev/null; then
    echo "❌ Qdrant 未启动，请运行: docker compose up -d qdrant"
    exit 1
fi

# 代码质量检查
echo "🔍 代码质量检查..."
uv run ruff check .
uv run ruff format --check .
uv run mypy app/

# 运行测试
echo "🧪 运行单元测试..."
uv run pytest tests/unit/ -v

echo "🔗 运行集成测试..."
uv run pytest tests/integration/ -v

# 可选：运行端到端测试
if [ "$1" = "--e2e" ]; then
    echo "🌐 运行端到端测试..."
    # 启动 API 服务
    uv run uvicorn app.main:app --port 8020 &
    API_PID=$!
    
    # 等待服务启动
    sleep 5
    
    # 运行 E2E 测试
    API_BASE=http://localhost:8020 \
    uv run pytest test/test_live_e2e.py -v
    
    # 停止 API 服务
    kill $API_PID
fi

echo "✅ 所有测试通过！"
```

## 测试最佳实践

### 测试编写原则

1. **独立性**：每个测试应该独立运行，不依赖其他测试
2. **确定性**：测试结果应该是可重复的，避免随机性
3. **快速性**：单元测试应该快速执行，避免耗时操作
4. **清晰性**：测试名称和断言应该清楚表达测试意图

### Mock 使用指南

```python
# 正确的 Mock 使用示例
@pytest.mark.asyncio
async def test_embedding_service_with_mock():
    with patch('app.infra.embeddings.get_embedding') as mock_embed:
        # 设置 Mock 返回值
        mock_embed.return_value = [0.1, 0.2, 0.3]
        
        # 执行测试
        result = await some_function_that_uses_embedding()
        
        # 验证结果和调用
        assert result is not None
        mock_embed.assert_called_once_with("test text")
```

### 测试数据管理

1. **使用 Fixtures**：为常用的测试数据创建 pytest fixtures
2. **数据隔离**：每个测试使用独立的数据，避免相互影响
3. **清理策略**：测试结束后及时清理数据，避免污染
4. **真实数据**：集成测试使用接近真实的数据

### 性能测试注意事项

1. **基准测试**：建立性能基准，监控性能回归
2. **负载测试**：模拟真实的负载情况
3. **资源监控**：监控 CPU、内存、数据库连接等资源使用
4. **瓶颈分析**：识别和分析性能瓶颈

通过遵循这些测试指南，可以确保系统的质量和稳定性。