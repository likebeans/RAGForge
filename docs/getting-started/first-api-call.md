# 第一个 API 调用

本指南将详细介绍如何进行第一个 API 调用，包括认证、基本操作和错误处理。

## 前提条件

- Self-RAG Pipeline 服务已启动并运行在 `http://localhost:8020`
- 已获取有效的 API Key

## API 认证

### 获取 API Key

如果还没有 API Key，需要先创建租户：

```bash
# 使用管理员令牌创建租户
curl -X POST "http://localhost:8020/admin/tenants" \
  -H "X-Admin-Token: your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-first-tenant"}'
```

响应中会包含初始的 API Key：
```json
{
  "id": "tenant-uuid",
  "name": "my-first-tenant",
  "status": "active",
  "initial_api_key": "kb_sk_xxxxxxxxxxxxxxxxx"
}
```

### 认证方式

所有 API 调用都需要在请求头中包含 Bearer Token：

```bash
Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx
```

## 基础 API 调用

### 1. 健康检查

首先验证服务是否正常运行：

```bash
# 存活检查
curl -X GET "http://localhost:8020/health"
```

**预期响应**：
```json
{
  "status": "ok"
}
```

```bash
# 就绪检查（包含依赖服务状态）
curl -X GET "http://localhost:8020/ready"
```

**预期响应**：
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "message": "connected"},
    "qdrant": {"status": "ok", "message": "connected (0 collections)"}
  },
  "timestamp": "2024-12-08T10:00:00.000Z"
}
```

### 2. 创建知识库

```bash
curl -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的第一个知识库",
    "description": "用于测试的知识库"
  }'
```

**预期响应**：
```json
{
  "id": "kb-uuid-here",
  "name": "我的第一个知识库",
  "description": "用于测试的知识库",
  "status": "active",
  "config": {
    "chunker": "sliding_window",
    "chunker_params": {"window": 1024, "overlap": 100},
    "retriever": "hybrid"
  },
  "created_at": "2024-12-08T10:00:00Z",
  "updated_at": "2024-12-08T10:00:00Z"
}
```

保存知识库 ID 用于后续调用：
```bash
export KB_ID="kb-uuid-here"
```

### 3. 上传文档

```bash
curl -X POST "http://localhost:8020/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python 编程基础",
    "content": "Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年首次发布。Python 设计哲学强调代码的可读性和简洁的语法。Python 支持多种编程范式，包括面向对象、命令式、函数式和过程式编程。Python 拥有丰富的标准库，被广泛应用于 Web 开发、数据分析、人工智能、科学计算等领域。",
    "metadata": {
      "category": "编程语言",
      "level": "基础",
      "author": "示例作者"
    }
  }'
```

**预期响应**：
```json
{
  "id": "doc-uuid-here",
  "title": "Python 编程基础",
  "knowledge_base_id": "kb-uuid-here",
  "status": "processing",
  "metadata": {
    "category": "编程语言",
    "level": "基础",
    "author": "示例作者"
  },
  "created_at": "2024-12-08T10:01:00Z",
  "processing_status": "pending"
}
```

### 4. 检查文档处理状态

文档上传后需要时间进行切分和索引，可以检查处理状态：

```bash
curl -X GET "http://localhost:8020/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx"
```

等待文档状态变为 `completed`：
```json
{
  "documents": [
    {
      "id": "doc-uuid-here",
      "title": "Python 编程基础",
      "status": "completed",
      "processing_status": "completed",
      "chunk_count": 3
    }
  ]
}
```

### 5. 执行检索

```bash
curl -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 有什么特点？",
    "knowledge_base_ids": ["'$KB_ID'"],
    "top_k": 3
  }'
```

**预期响应**：
```json
{
  "results": [
    {
      "chunk_id": "chunk-uuid-1",
      "text": "Python 设计哲学强调代码的可读性和简洁的语法。Python 支持多种编程范式，包括面向对象、命令式、函数式和过程式编程。",
      "score": 0.85,
      "metadata": {
        "kb_id": "kb-uuid-here",
        "doc_id": "doc-uuid-here",
        "title": "Python 编程基础",
        "category": "编程语言"
      },
      "knowledge_base_id": "kb-uuid-here"
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "retriever": "hybrid"
  }
}
```

### 6. RAG 生成

```bash
curl -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 适合用于哪些应用场景？",
    "knowledge_base_ids": ["'$KB_ID'"],
    "temperature": 0.7
  }'
```

**预期响应**：
```json
{
  "answer": "根据文档内容，Python 被广泛应用于以下场景：\n\n1. **Web 开发** - 可以构建网站和 Web 应用\n2. **数据分析** - 处理和分析大量数据\n3. **人工智能** - 机器学习和深度学习项目\n4. **科学计算** - 数值计算和科学研究\n\nPython 的这些应用场景得益于其简洁的语法、丰富的标准库以及活跃的社区支持。",
  "sources": [
    {
      "chunk_id": "chunk-uuid-1",
      "text": "Python 拥有丰富的标准库，被广泛应用于 Web 开发、数据分析、人工智能、科学计算等领域。",
      "score": 0.92,
      "knowledge_base_id": "kb-uuid-here",
      "document_id": "doc-uuid-here"
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "retriever": "hybrid"
  },
  "retrieval_count": 1
}
```

## OpenAI 兼容接口

### Embeddings API

```bash
curl -X POST "http://localhost:8020/v1/embeddings" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Python 是一种编程语言",
    "model": "text-embedding-v3"
  }'
```

**预期响应**：
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.0023, -0.0091, 0.0041, ...]
    }
  ],
  "model": "bge-m3",
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 6
  }
}
```

### Chat Completions API

```bash
curl -X POST "http://localhost:8020/v1/chat/completions" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Python 和 Java 有什么区别？"}
    ],
    "knowledge_base_ids": ["'$KB_ID'"],
    "temperature": 0.7
  }'
```

**预期响应**：
```json
{
  "id": "chatcmpl-uuid",
  "object": "chat.completion",
  "created": 1701234567,
  "model": "qwen3:14b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "基于知识库中的信息，Python 和 Java 的主要区别包括：\n\n1. **语法复杂度**：Python 强调代码的可读性和简洁的语法，而 Java 语法相对复杂\n2. **编程范式**：Python 支持多种编程范式（面向对象、函数式、过程式），Java 主要是面向对象\n3. **应用领域**：Python 广泛用于数据分析、AI、科学计算，Java 更多用于企业级应用开发"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 120,
    "total_tokens": 170
  },
  "references": [
    {
      "chunk_id": "chunk-uuid-1",
      "text": "Python 设计哲学强调代码的可读性和简洁的语法...",
      "score": 0.85
    }
  ]
}
```

## 错误处理

### 常见错误响应

#### 1. 认证失败 (401)

```bash
curl -X GET "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer invalid-key"
```

**错误响应**：
```json
{
  "error": {
    "message": "Invalid API key provided",
    "type": "invalid_request_error",
    "code": "invalid_api_key"
  }
}
```

#### 2. 权限不足 (403)

```bash
# 使用只读权限的 API Key 尝试创建知识库
curl -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer kb_sk_readonly_key" \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}'
```

**错误响应**：
```json
{
  "error": {
    "message": "Insufficient permissions for this operation",
    "type": "permission_error",
    "code": "insufficient_permissions"
  }
}
```

#### 3. 资源不存在 (404)

```bash
curl -X GET "http://localhost:8020/v1/knowledge-bases/non-existent-id" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx"
```

**错误响应**：
```json
{
  "error": {
    "message": "Knowledge base not found",
    "type": "not_found_error",
    "code": "resource_not_found"
  }
}
```

#### 4. 请求参数错误 (422)

```bash
curl -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"description": "缺少必需的 name 字段"}'
```

**错误响应**：
```json
{
  "error": {
    "message": "Validation error",
    "type": "validation_error",
    "code": "invalid_request_data",
    "details": [
      {
        "field": "name",
        "message": "Field required"
      }
    ]
  }
}
```

#### 5. 限流错误 (429)

```bash
# 超过每分钟请求限制
```

**错误响应**：
```json
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded",
    "retry_after": 60
  }
}
```

## 使用 cURL 的最佳实践

### 1. 设置环境变量

```bash
# 设置基础配置
export API_BASE="http://localhost:8020"
export API_KEY="kb_sk_xxxxxxxxxxxxxxxxx"

# 使用变量简化命令
curl -X GET "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"
```

### 2. 保存响应到文件

```bash
# 保存响应用于调试
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "knowledge_base_ids": ["'$KB_ID'"]}' \
  -o response.json

# 查看格式化的响应
cat response.json | jq .
```

### 3. 显示详细信息

```bash
# 显示请求和响应头
curl -v -X GET "$API_BASE/health"

# 只显示响应头
curl -I -X GET "$API_BASE/health"

# 显示响应时间
curl -w "@curl-format.txt" -X GET "$API_BASE/health"
```

创建 `curl-format.txt` 文件：
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

## 调试技巧

### 1. 检查服务状态

```bash
# 检查所有健康指标
curl -s "$API_BASE/metrics" | jq .

# 检查特定服务状态
curl -s "$API_BASE/ready" | jq '.checks'
```

### 2. 验证 API Key 权限

```bash
# 列出当前 API Key 可访问的知识库
curl -X GET "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" | jq '.[] | {id, name}'
```

### 3. 测试不同检索器

```bash
# 测试所有检索器类型
for retriever in dense bm25 hybrid hyde fusion; do
  echo "Testing $retriever retriever:"
  curl -s -X POST "$API_BASE/v1/retrieve" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "test query",
      "knowledge_base_ids": ["'$KB_ID'"],
      "retriever_override": {"name": "'$retriever'"}
    }' | jq '.model.retriever'
done
```

## 下一步

完成第一个 API 调用后，您可以：

1. 探索[开发文档](../development/)了解高级功能
2. 查看[架构文档](../architecture/)理解系统设计
3. 学习[Python SDK](../../sdk/README.md)简化开发
4. 阅读[API 规范](../architecture/api-specification.md)了解完整接口

## 相关资源

- [快速开始指南](quick-start.md)
- [配置指南](configuration.md)
- [错误代码参考](../reference/error-codes.md)
- [API 限制说明](../reference/api-limits.md)