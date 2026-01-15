# API 规范文档

本文档详细描述 Self-RAG Pipeline 的 API 设计规范、接口定义和使用指南。

## 接口设计原则

### 统一约定

- **认证方式**：`Authorization: Bearer <api_key>`，所有接口除 `/healthz` 外均需携带
- **内容类型**：`application/json`；当前阶段仅支持 JSON 文本上传
- **ID 规范**：全部使用 UUID 字符串；文档 ID 全局唯一，服务端会校验所属租户/知识库
- **时间格式**：ISO 8601（UTC）
- **列表约定**：响应统一返回 `items` 与 `total`；分页使用 `page`(>=1) 与 `page_size`(<=100) 作为查询参数
- **错误响应**：`{"detail": "错误信息", "code": "ERROR_CODE"}`

### 错误码规范

| 错误码 | 场景 |
|--------|------|
| `INVALID_API_KEY` | API Key 无效或已吊销 |
| `UNAUTHORIZED` | 缺少授权头 |
| `KB_NOT_FOUND` | 知识库不存在或不属于当前租户 |
| `DOC_NOT_FOUND` | 文档不存在或不属于当前租户/知识库 |
| `CHUNK_NOT_FOUND` | Chunk 不存在 |
| `KB_CONFIG_ERROR` | 多知识库检索配置不一致 |
| `VALIDATION_ERROR` | 参数校验失败 |
| `API_KEY_NOT_FOUND` | API Key 不存在 |
| `FETCH_FAILED` | 从 URL 拉取文档失败 |
| `INTERNAL_ERROR` | 未捕获的服务端异常 |

## 核心 API 接口

### 知识库管理

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/v1/knowledge-bases` | 创建知识库 | ✅ 已实现 |
| `GET` | `/v1/knowledge-bases` | 列出知识库 | ✅ 已实现 |
| `GET` | `/v1/knowledge-bases/{id}` | 获取知识库详情 | ✅ 已实现 |
| `PATCH` | `/v1/knowledge-bases/{id}` | 更新知识库配置 | ✅ 已实现 |
| `DELETE` | `/v1/knowledge-bases/{id}` | 删除知识库 | ✅ 已实现 |

### 文档管理

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/v1/knowledge-bases/{id}/documents` | 上传文档（JSON） | ✅ 已实现 |
| `POST` | `/v1/knowledge-bases/{id}/documents/upload` | 文件直传（multipart） | ✅ 已实现 |
| `POST` | `/v1/knowledge-bases/{id}/documents/batch` | 批量上传（最多50个） | ✅ 已实现 |
| `GET` | `/v1/knowledge-bases/{id}/documents` | 列出文档 | ✅ 已实现 |
| `GET` | `/v1/documents/{id}` | 获取文档详情 | ✅ 已实现 |
| `DELETE` | `/v1/documents/{id}` | 删除文档 | ✅ 已实现 |

### Chunk 管理

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `GET` | `/v1/documents/{id}/chunks` | 列出文档 Chunks | ✅ 已实现 |

### 检索与生成

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/v1/retrieve` | 语义检索 | ✅ 已实现 |
| `POST` | `/v1/rag` | RAG 生成 | ✅ 已实现 |

### API Key 管理

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/v1/api-keys` | 创建 API Key | ✅ 已实现 |
| `GET` | `/v1/api-keys` | 列出 API Keys | ✅ 已实现 |
| `PATCH` | `/v1/api-keys/{id}` | 更新 API Key | ✅ 已实现 |
| `POST` | `/v1/api-keys/{id}/revoke` | 吊销 API Key | ✅ 已实现 |

## 关键接口详解

### 语义检索接口

**端点**：`POST /v1/retrieve`

**请求参数**：
- `query` (string, required)：查询语句
- `knowledge_base_ids` (string[], required)：目标知识库 ID 列表，必须显式传入
- `top_k` (int, optional, 默认 5，范围 1-50)：返回数量
- `score_threshold` (float, optional, 0-1)：低于该分数的结果将被过滤
- `metadata_filter` (object, optional)：按元数据精确匹配过滤结果

**示例请求**：
```json
{
  "query": "孕妇可以吃这个药吗",
  "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"],
  "top_k": 3,
  "score_threshold": 0.6,
  "metadata_filter": {"source": "markdown"}
}
```

**示例响应**：
```json
{
  "results": [
    {
      "chunk_id": "c1",
      "text": "孕妇禁用",
      "score": 0.65,
      "metadata": {"title": "复方南五加口服液说明书"},
      "knowledge_base_id": "2da0774b-c20e-416e-8e9b-33032db806a7",
      "document_id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
      "context_text": null
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "rerank_provider": null,
    "rerank_model": null,
    "retriever": "hybrid"
  }
}
```

### 文档上传接口

**端点**：`POST /v1/knowledge-bases/{id}/documents`

**请求参数**：
- `title` (string, required)：文档标题
- `content` (string, conditionally required)：纯文本内容（与 `source_url` 至少提供一个）
- `source_url` (string, optional)：从 URL 拉取文本内容
- `metadata` (object, optional)：文档元数据
- `source` (string, optional)：来源类型，如 `pdf/docx/url/text`

**示例请求**：
```json
{
  "title": "复方南五加口服液说明书",
  "content": "全文内容...",
  "metadata": {"category": "drug_instruction"},
  "source": "markdown"
}
```

**示例响应**：
```json
{
  "document_id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
  "chunk_count": 59
}
```

### 文档详情接口

**端点**：`GET /v1/documents/{id}`

**返回字段**：
- `id`, `title`, `knowledge_base_id`, `source`, `metadata`
- `chunk_count`, `created_at`
- `summary`（可选）、`summary_status`：`pending/generating/completed/failed/skipped`

**示例响应**：
```json
{
  "id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
  "title": "复方南五加口服液说明书",
  "knowledge_base_id": "2da0774b-c20e-416e-8e9b-33032db806a7",
  "source": "markdown",
  "metadata": {"category": "drug_instruction"},
  "chunk_count": 59,
  "summary_status": "generating",
  "summary": null,
  "created_at": "2025-12-02T07:10:03.618518Z"
}
```

## OpenAI 兼容接口

项目提供完整的 OpenAI 兼容 API，支持：

### Chat Completions

**端点**：`POST /v1/chat/completions`

**特殊参数**：
- `knowledge_base_ids` (string[], optional)：启用 RAG 检索的知识库列表
- `retrieval_config` (object, optional)：检索配置覆盖

**示例请求**：
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Python 有什么应用？"}
  ],
  "knowledge_base_ids": ["kb1"],
  "retrieval_config": {
    "top_k": 5,
    "retriever": "hybrid"
  }
}
```

### Embeddings

**端点**：`POST /v1/embeddings`

**示例请求**：
```json
{
  "model": "text-embedding-3-small",
  "input": ["文本1", "文本2"]
}
```

## 管理员接口

通过 `X-Admin-Token` 头认证的管理接口：

### 租户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/tenants` | 创建租户 |
| GET | `/admin/tenants` | 列出租户 |
| GET | `/admin/tenants/{id}` | 租户详情 |
| PATCH | `/admin/tenants/{id}` | 更新租户 |
| POST | `/admin/tenants/{id}/disable` | 禁用租户 |
| POST | `/admin/tenants/{id}/enable` | 启用租户 |
| DELETE | `/admin/tenants/{id}` | 删除租户 |
| GET | `/admin/tenants/{id}/api-keys` | 列出 API Keys |
| POST | `/admin/tenants/{id}/api-keys` | 创建 API Key |

### 系统配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/system-config` | 获取所有系统配置 |
| GET | `/admin/system-config/{key}` | 获取单个配置 |
| PUT | `/admin/system-config/{key}` | 更新配置（立即生效） |
| POST | `/admin/system-config/reset` | 重置为环境变量默认值 |

## 响应格式规范

### 列表响应

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

### 错误响应

```json
{
  "detail": "错误信息",
  "code": "ERROR_CODE"
}
```

### 成功响应

- 创建操作：返回 201 状态码和创建的资源
- 更新操作：返回 200 状态码和更新后的资源
- 删除操作：返回 204 状态码（无内容）
- 查询操作：返回 200 状态码和查询结果

## API Key 角色权限

| 角色 | 说明 |
|------|------|
| `admin` | 全部权限 + 管理 API Key |
| `write` | 创建/删除 KB、上传文档、检索 |
| `read` | 仅检索和列表 |

## 限流与配额

- 默认限流：120 次/分钟
- 可按 API Key 独立配置
- 支持 Redis 集群限流（生产环境推荐）

## 安全注意事项

- API Key 使用 SHA256 哈希存储，不保存明文
- 所有接口需要 Bearer Token 认证
- 生产环境应启用 HTTPS
- 支持 ACL 和敏感度级别的文档访问控制

## 版本兼容性

- API 版本：v1
- 向后兼容：新增字段不影响现有客户端
- 破坏性变更：通过新版本号发布