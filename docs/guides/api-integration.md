# RAGForge API 对接文档

> **更新时间**: 2026-02-09  
> **测试环境**: http://192.168.168.105:8020

## 概述

RAGForge 提供以下核心 API 接口供 Agent 服务对接：

| 接口 | 路径 | 说明 |
|------|------|------|
| 知识库管理 | `/v1/knowledge-bases` | 创建、查询、删除知识库 |
| 文档管理 | `/v1/knowledge-bases/{kb_id}/documents` | 上传、查询、删除文档 |
| **检索 API** | `/v1/retrieve` | 从知识库检索相关文档片段 |
| **RAG 生成 API** | `/v1/rag` | 结合检索和 LLM 生成回答 |
| **流式 RAG API** | `/v1/rag/stream` | SSE 流式 RAG 生成 |
| **OpenAI 兼容 Chat** | `/v1/chat/completions` | OpenAI 兼容的聊天接口（RAG 模式） |
| **OpenAI 兼容 Embeddings** | `/v1/embeddings` | OpenAI 兼容的向量化接口 |

## 认证

所有 API 请求需要在 Header 中携带 API Key：

```
Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxx
```

### API Key 创建与 Identity 配置

创建 API Key 时可以指定 `identity` 信息，用于 ACL 权限控制：

```bash
curl -X POST "http://192.168.168.105:8020/v1/api-keys" \
  -H "Authorization: Bearer kb_sk_admin_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "财务部门Key",
    "role": "read",
    "identity": {
      "user_id": "finance_user_001",
      "roles": ["finance"],
      "clearance": "restricted"
    }
  }'
```

**Identity 字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `user_id` | string | 用户唯一标识 | `"finance_user_001"` |
| `roles` | string[] | 用户角色列表 | `["finance", "admin"]` |
| `groups` | string[] | 用户组列表（可选） | `["sales", "engineering"]` |
| `clearance` | string | 安全许可级别 | `public` / `internal` / `restricted` |

**Clearance 级别**：
- `public`: 只能访问公开文档
- `internal`: 可访问公开和内部文档
- `restricted`: 可访问所有级别文档（需匹配 ACL 规则）

**完整示例**：

```bash
# 普通用户（只能看 public）
curl -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "普通用户Key",
    "role": "read",
    "identity": {
      "user_id": "public_user_001",
      "roles": [],
      "clearance": "public"
    }
  }'

# 财务人员（可访问 finance 机密）
curl -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "财务Key",
    "role": "read",
    "identity": {
      "user_id": "finance_user_001",
      "roles": ["finance"],
      "clearance": "restricted"
    }
  }'

# 技术人员（可访问 tech/engineering 机密）
curl -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术Key",
    "role": "read",
    "identity": {
      "user_id": "tech_user_001",
      "roles": ["tech", "engineering"],
      "clearance": "restricted"
    }
  }'
```

## Base URL

```
http://192.168.168.105:8020
```

---

## 0. 知识库管理 API

### 0.1 获取知识库列表

```bash
curl -H "Authorization: Bearer kb_sk_xxx" \
  "http://192.168.168.105:8020/v1/knowledge-bases"
```

**真实响应**:
```json
{
  "items": [
    {
      "id": "49a060ff-3fc0-4ec1-aeec-ae5990531f36",
      "name": "test",
      "description": null,
      "config": {
        "embedding": {
          "provider": "siliconflow",
          "model": "Qwen/Qwen3-Embedding-4B"
        }
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 0.2 创建知识库

```bash
curl -X POST -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-kb", "description": "测试知识库"}' \
  "http://192.168.168.105:8020/v1/knowledge-bases"
```

**真实响应**:
```json
{
  "id": "017f07fe-a56d-41e5-9708-5e88a269664d",
  "name": "my-kb",
  "description": "测试知识库",
  "config": {}
}
```

### 0.3 获取文档列表

```bash
curl -H "Authorization: Bearer kb_sk_xxx" \
  "http://192.168.168.105:8020/v1/knowledge-bases/{kb_id}/documents"
```

**真实响应**:
```json
{
  "items": [
    {
      "id": "c8e53f53-50be-4390-870f-4dca10208075",
      "title": "典恒产品彩页_5.典恒金崮膏海报彩页",
      "knowledge_base_id": "49a060ff-3fc0-4ec1-aeec-ae5990531f36",
      "metadata": {
        "original_filename": "典恒产品彩页_5.典恒金崮膏海报彩页.md",
        "file_size": 968
      },
      "source": "file:md",
      "chunk_count": 2,
      "processing_status": "completed",
      "created_at": "2026-01-20T07:07:21.844939Z"
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20
}
```

### 0.4 上传文档

RAGForge 提供两种文档上传方式：

#### 方式1：文件直传（推荐）

使用 `multipart/form-data` 上传文件流：

```bash
curl -X POST "http://192.168.168.105:8020/v1/knowledge-bases/{kb_id}/documents/upload" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -F "file=@document.txt" \
  -F "title=我的文档"
```

**支持的文件类型**: `.txt`, `.md`, `.markdown`, `.json`  
**文件大小限制**: 10MB  
**编码要求**: UTF-8

#### 方式2：JSON 上传（传入文本内容）

```bash
curl -X POST "http://192.168.168.105:8020/v1/knowledge-bases/{kb_id}/documents" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试文档",
    "content": "这是文档内容...",
    "source": "api"
  }'
```

或从 URL 拉取内容：

```bash
curl -X POST "http://192.168.168.105:8020/v1/knowledge-bases/{kb_id}/documents" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "远程文档",
    "source_url": "https://example.com/doc.txt"
  }'
```

#### 方式3：带 ACL 权限控制的文档上传

RAGForge 支持文档级访问控制（ACL），可以限制不同身份的用户访问特定文档：

```bash
curl -X POST "http://192.168.168.105:8020/v1/knowledge-bases/{kb_id}/documents" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "财务机密文档",
    "content": "这是财务部门的机密预算报告...",
    "sensitivity_level": "restricted",
    "acl_roles": ["finance", "admin"]
  }'
```

**ACL 字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `sensitivity_level` | string | 敏感度级别 | `public` / `internal` / `restricted` |
| `acl_roles` | string[] | 允许访问的角色列表 | `["finance", "admin"]` |
| `acl_users` | string[] | 允许访问的用户 ID 列表 | `["user_001", "user_002"]` |
| `acl_groups` | string[] | 允许访问的用户组列表 | `["sales", "engineering"]` |

**敏感度级别**：
- `public`: 公开文档，所有人可见
- `internal`: 内部文档，需要 `clearance >= internal`
- `restricted`: 机密文档，需要 `clearance >= restricted` 且匹配 ACL 规则

**完整示例**：

```bash
# 公开文档
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "公司简介",
    "content": "这是公开的公司介绍...",
    "sensitivity_level": "public"
  }'

# 财务机密（只允许 finance 角色）
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "年度预算报告",
    "content": "2025年财务预算...",
    "sensitivity_level": "restricted",
    "acl_roles": ["finance"]
  }'

# 技术文档（允许多个角色）
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "系统架构文档",
    "content": "核心架构设计...",
    "sensitivity_level": "restricted",
    "acl_roles": ["tech", "engineering", "admin"]
  }'

# 指定用户访问
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "个人绩效报告",
    "content": "员工绩效评估...",
    "sensitivity_level": "restricted",
    "acl_users": ["user_zhang_san", "user_manager_001"]
  }'
```

> ⚠️ **重要提示**：
> - 字段名是 `acl_roles`、`acl_users`、`acl_groups`，不是 `acl_allow_*`
> - ACL 过滤在检索时自动生效，无需额外配置
> - API Key 需要包含 `identity` 信息才能进行 ACL 匹配

---

## 1. 检索 API

### 接口信息

| 项目 | 值 |
|------|-----|
| **URL** | `POST /v1/retrieve` |
| **认证** | Bearer Token |
| **Content-Type** | application/json |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 查询语句 |
| `knowledge_base_ids` | string[] | ✅ | 知识库 ID 列表 |
| `top_k` | int | ❌ | 返回结果数量（默认 5，最大 50） |
| `score_threshold` | float | ❌ | 分数阈值过滤（0-1） |
| `retriever_override` | object | ❌ | 临时覆盖检索器配置 |
| `rerank` | bool | ❌ | 是否启用 Rerank（默认 false） |
| `rerank_top_k` | int | ❌ | Rerank 后返回数量 |

### 请求示例

```bash
curl -X POST "http://192.168.168.105:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "关节疼痛用什么产品",
    "knowledge_base_ids": ["49a060ff-3fc0-4ec1-aeec-ae5990531f36"],
    "top_k": 3
  }'
```

### 真实响应示例

```json
{
  "results": [
    {
      "chunk_id": "1c881e70-2915-4c6b-9e52-2a1c8f188e23",
      "text": "# 古方智慧·科学组方\n\n承医圣李时珍养生精髓，严选二十二味道地本草，三效协同直击关节根源\n\n# 智能熬膏·匠心品质\n\n遵循古法八繁之功，72 小时慢熬凝萃...",
      "score": 0.5095,
      "metadata": {
        "title": "典恒产品彩页_5.典恒金崮膏海报彩页",
        "original_filename": "典恒产品彩页_5.典恒金崮膏海报彩页.md",
        "chunk_index": 0,
        "total_chunks": 2
      },
      "knowledge_base_id": "49a060ff-3fc0-4ec1-aeec-ae5990531f36",
      "document_id": "c8e53f53-50be-4390-870f-4dca10208075"
    }
  ],
  "model": {
    "embedding_provider": "siliconflow",
    "embedding_model": "Qwen/Qwen3-Embedding-4B",
    "retriever": "dense"
  }
}
```

### 高级：使用不同检索器

```bash
# 使用 HyDE 检索（LLM 生成假设文档）
curl -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何优化数据库性能？",
    "knowledge_base_ids": ["kb-id"],
    "top_k": 5,
    "retriever_override": {
      "name": "hyde",
      "params": {"base_retriever": "dense"}
    }
  }'

# 使用混合检索（Dense + BM25）
curl -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PostgreSQL 索引类型",
    "knowledge_base_ids": ["kb-id"],
    "retriever_override": {
      "name": "hybrid"
    }
  }'
```

---

## 2. RAG 聊天 API

### 接口信息

| 项目 | 值 |
|------|-----|
| **URL** | `POST /v1/rag` |
| **认证** | Bearer Token |
| **Content-Type** | application/json |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 用户问题 |
| `knowledge_base_ids` | string[] | ✅ | 知识库 ID 列表 |
| `top_k` | int | ❌ | 检索结果数量（默认 5） |
| `system_prompt` | string | ❌ | 自定义系统提示词 |
| `temperature` | float | ❌ | LLM 温度（0-2，默认 0.7） |
| `max_tokens` | int | ❌ | 最大生成 token 数 |
| `llm_override` | object | ❌ | 临时覆盖 LLM 配置 |
| `include_sources` | bool | ❌ | 是否返回检索来源（默认 true） |

### 请求示例

```bash
curl -X POST "http://192.168.168.105:8020/v1/rag" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "关节疼痛用什么产品比较好？",
    "knowledge_base_ids": ["49a060ff-3fc0-4ec1-aeec-ae5990531f36"],
    "top_k": 3
  }'
```

### 真实响应示例

```json
{
  "answer": "根据提供的参考资料，针对**关节疼痛**问题，推荐使用：\n\n### ✅ **典恒金崮膏**\n\n**理由如下：**\n- 明确宣称\"三效协同直击关节根源\"，主打改善关节健康；\n- 适用人群中包含：久坐族、中老年、运动人群、湿寒体质——这些群体常伴有关节不适或疼痛；\n- 组方理念源自\"医圣李时珍养生精髓\"，严选二十二味道地本草...\n\n⚠️ 注意事项：\n- 不宜与藜芦同用；\n- 忌食高嘌呤食物、海鲜等...",
  "sources": [
    {
      "chunk_id": "1c881e70-2915-4c6b-9e52-2a1c8f188e23",
      "text": "# 古方智慧·科学组方\n\n承医圣李时珍养生精髓，严选二十二味道地本草，三效协同直击关节根源...",
      "score": 0.513,
      "knowledge_base_id": "49a060ff-3fc0-4ec1-aeec-ae5990531f36",
      "document_id": "c8e53f53-50be-4390-870f-4dca10208075",
      "metadata": {
        "title": "典恒产品彩页_5.典恒金崮膏海报彩页",
        "original_filename": "典恒产品彩页_5.典恒金崮膏海报彩页.md"
      }
    }
  ],
  "model": {
    "embedding_provider": "siliconflow",
    "embedding_model": "Qwen/Qwen3-Embedding-4B",
    "llm_provider": "qwen",
    "llm_model": "qwen-plus-2025-12-01",
    "retriever": "dense"
  },
  "retrieval_count": 3
}
```

### 高级：自定义 LLM 和提示词

```bash
curl -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer kb_sk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "总结一下这篇文档的要点",
    "knowledge_base_ids": ["kb-id"],
    "system_prompt": "你是一个专业的文档分析助手，请用简洁的语言回答问题。",
    "temperature": 0.3,
    "max_tokens": 1000,
    "llm_override": {
      "provider": "openai",
      "model": "gpt-4-turbo"
    }
  }'
```

---

## 2.5 流式 RAG API

### 接口信息

| 项目 | 值 |
|------|-----|
| **URL** | `POST /v1/rag/stream` |
| **认证** | Bearer Token |
| **Content-Type** | application/json |
| **响应格式** | Server-Sent Events (SSE) |

### 请求参数

与 `/v1/rag` 相同。

### 请求示例

```bash
curl -X POST "http://192.168.168.105:8020/v1/rag/stream" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这个产品有什么功效？",
    "knowledge_base_ids": ["53e84425-3516-44a5-be25-9a83cee2c156"]
  }'
```

### SSE 响应格式

```
event: sources
data: [{"text": "...", "score": 0.85, "chunk_id": "xxx", "knowledge_base_id": "xxx"}]

event: content
data: 根据

event: content
data: 参考资料

event: content
data: ，这款产品...

event: done
data: {"usage": {"prompt_tokens": 150, "completion_tokens": 80}}
```

**事件类型**：
- `sources`：检索到的文档来源（首次返回）
- `content`：LLM 生成的内容片段（流式输出）
- `done`：生成完成，包含 token 用量统计

---

## 3. OpenAI 兼容 API

RAGForge 提供与 OpenAI API 兼容的接口，方便现有应用快速对接。

### 3.1 Chat Completions（RAG 模式）

| 项目 | 值 |
|------|-----|
| **URL** | `POST /v1/chat/completions` |
| **认证** | Bearer Token |
| **Content-Type** | application/json |

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | ✅ | 模型名称（会被租户配置覆盖） |
| `messages` | array | ✅ | 消息列表 |
| `knowledge_base_ids` | string[] | ✅ | 知识库 ID 列表（RAG 模式必填） |
| `temperature` | float | ❌ | 温度参数（0-2） |
| `max_tokens` | int | ❌ | 最大生成 token 数 |
| `top_k` | int | ❌ | 检索结果数量（默认 5） |

#### 请求示例

```bash
curl -X POST "http://192.168.168.105:8020/v1/chat/completions" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-plus",
    "messages": [
      {"role": "user", "content": "这个知识库讲什么内容？"}
    ],
    "knowledge_base_ids": ["53e84425-3516-44a5-be25-9a83cee2c156"]
  }'
```

#### 响应示例

```json
{
  "id": "chatcmpl-56f4314d-62dc-4660-941d-b4504d0933fa",
  "object": "chat.completion",
  "created": 1770621977,
  "model": "qwen-plus",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "根据参考资料，这个知识库包含健康产品的文献资料..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225
  },
  "sources": [
    {
      "chunk_id": "xxx",
      "text": "...",
      "score": 0.85
    }
  ]
}
```

> ⚠️ **注意**：当前版本 `knowledge_base_ids` 为必填参数，纯 LLM 模式暂未实现。

### 3.2 Embeddings

| 项目 | 值 |
|------|-----|
| **URL** | `POST /v1/embeddings` |
| **认证** | Bearer Token |
| **Content-Type** | application/json |

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input` | string/array | ✅ | 要向量化的文本（单个或列表） |
| `model` | string | ❌ | 模型名称（使用租户默认配置） |

#### 请求示例

```bash
# 单个文本
curl -X POST "http://192.168.168.105:8020/v1/embeddings" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "测试文本",
    "model": "text-embedding-v3"
  }'

# 批量文本
curl -X POST "http://192.168.168.105:8020/v1/embeddings" \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "input": ["文本1", "文本2", "文本3"],
    "model": "text-embedding-v3"
  }'
```

#### 响应示例

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.0123, -0.0456, 0.0789, ...]
    }
  ],
  "model": "Qwen/Qwen3-Embedding-8B",
  "usage": {
    "prompt_tokens": 3,
    "total_tokens": 3
  }
}
```

> **说明**：响应中的 `model` 字段显示实际使用的模型（来自租户配置），可能与请求中指定的不同。

---

## 4. 错误码说明

| HTTP 状态码 | 错误码 | 说明 |
|------------|--------|------|
| 401 | `INVALID_API_KEY` | API Key 无效或未提供 |
| 403 | `KB_NOT_IN_SCOPE` | API Key 无权访问指定知识库 |
| 403 | `NO_PERMISSION` | 检索结果被 ACL 权限过滤 |
| 404 | `KB_NOT_FOUND` | 知识库不存在 |
| 400 | `KB_CONFIG_ERROR` | 知识库配置错误 |
| 500 | `RAG_FAILED` | RAG 生成失败 |

### 错误响应格式

```json
{
  "detail": {
    "code": "KB_NOT_FOUND",
    "detail": "One or more knowledge bases not found for tenant"
  }
}
```

### ACL 权限过滤说明

当使用带 `identity` 的 API Key 检索时，系统会自动进行 ACL 过滤：

**过滤规则**：
1. **Public 文档**：所有人可见
2. **Internal 文档**：需要 `clearance >= internal`
3. **Restricted 文档**：需要 `clearance >= restricted` 且满足以下任一条件：
   - 用户 ID 在 `acl_users` 列表中
   - 用户角色在 `acl_roles` 列表中
   - 用户组在 `acl_groups` 列表中

**示例场景**：

```bash
# 场景1：财务人员检索（可看到 finance 机密）
curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_finance_xxx" \
  -d '{"query":"预算","knowledge_base_ids":["kb1"]}'

# 返回：public 文档 + finance 机密文档

# 场景2：普通用户检索（只能看 public）
curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_public_xxx" \
  -d '{"query":"预算","knowledge_base_ids":["kb1"]}'

# 返回：仅 public 文档
```

**注意事项**：
- ACL 过滤在向量检索之后进行，可能导致返回结果少于 `top_k`
- 如果所有检索结果都被 ACL 过滤，返回 `403 NO_PERMISSION`
- Admin 角色的 API Key 可以绕过 ACL 限制

---

## 5. Python 快速接入代码

```python
import requests

# 配置
BASE_URL = "http://192.168.168.105:8020"
API_KEY = "kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
KB_ID = "49a060ff-3fc0-4ec1-aeec-ae5990531f36"

# 1. 检索 API
def retrieve(query: str, kb_ids: list[str], top_k: int = 5) -> dict:
    """从知识库检索相关文档片段"""
    resp = requests.post(
        f"{BASE_URL}/v1/retrieve",
        headers=HEADERS,
        json={"query": query, "knowledge_base_ids": kb_ids, "top_k": top_k}
    )
    resp.raise_for_status()
    return resp.json()

# 2. RAG 生成 API
def rag(query: str, kb_ids: list[str], top_k: int = 5) -> dict:
    """检索 + LLM 生成回答"""
    resp = requests.post(
        f"{BASE_URL}/v1/rag",
        headers=HEADERS,
        json={"query": query, "knowledge_base_ids": kb_ids, "top_k": top_k}
    )
    resp.raise_for_status()
    return resp.json()

# 3. 获取知识库列表
def list_knowledge_bases() -> dict:
    resp = requests.get(f"{BASE_URL}/v1/knowledge-bases", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


# ===== 使用示例 =====
if __name__ == "__main__":
    # 列出知识库
    kbs = list_knowledge_bases()
    print(f"知识库数量: {kbs['total']}")
    for kb in kbs["items"]:
        print(f"  - {kb['name']} ({kb['id']})")
    
    # 检索
    result = retrieve("关节疼痛用什么产品", [KB_ID], top_k=3)
    print(f"\n检索结果 ({len(result['results'])} 条):")
    for r in result["results"]:
        print(f"  [{r['score']:.3f}] {r['text'][:80]}...")
    
    # RAG 生成
    rag_result = rag("关节疼痛用什么产品比较好？", [KB_ID], top_k=3)
    print(f"\nRAG 回答:\n{rag_result['answer'][:500]}...")
```

### Agent 服务对接建议

```python
# 在 Agent 中使用检索结果作为上下文
def agent_with_rag(user_query: str, kb_ids: list[str]):
    # 方式1：仅检索，自行组织 prompt
    retrieval = retrieve(user_query, kb_ids, top_k=5)
    context = "\n\n".join([r["text"] for r in retrieval["results"]])
    # 传给你的 Agent 使用...
    
    # 方式2：直接使用 RAG API 获取答案
    rag_result = rag(user_query, kb_ids, top_k=5)
    return rag_result["answer"], rag_result["sources"]
```

---

## 6. 检索器类型

| 检索器 | 说明 | 适用场景 |
|--------|------|---------|
| `dense` | 稠密向量检索 | 语义相似（默认） |
| `bm25` | BM25 稀疏检索 | 精确关键词匹配 |
| `hybrid` | Dense + BM25 混合 | 通用问答（推荐） |
| `hyde` | HyDE（LLM 生成假设文档） | 复杂语义问题 |
| `multi_query` | 多查询扩展 | 提高召回率 |
| `fusion` | 融合检索 + Rerank | 高质量召回 |

---

## 7. 健康检查

```bash
curl http://localhost:8020/health
```

响应：
```json
{
  "status": "healthy",
  "version": "0.2.0"
}
```

---

## 8. 模型配置优先级

RAGForge 的模型配置（Embedding/LLM/Rerank）遵循以下优先级规则：

### 8.1 配置优先级

| 模型类型 | 优先级（从高到低） |
|----------|-------------------|
| **Embedding** | 请求参数 > 知识库配置 > 租户默认配置 > 环境变量 |
| **LLM** | 请求参数 > 租户默认配置 > 环境变量 |
| **Rerank** | 请求参数 > 租户默认配置 > 环境变量 |

### 8.2 配置来源说明

1. **请求参数** (`*_override`)：API 请求中传入的覆盖配置
2. **知识库配置**：创建知识库时指定的 `config.embedding`
3. **租户默认配置**：前端设置页面同步到服务器的 `model_settings.defaults`
4. **环境变量**：Docker 环境变量（如 `EMBEDDING_PROVIDER`、`LLM_PROVIDER`）

### 8.3 查看当前租户配置

```bash
curl -H "Authorization: Bearer kb_sk_xxx" \
  "http://192.168.168.105:8020/v1/settings/models"
```

响应：
```json
{
  "providers": {
    "siliconflow": {
      "api_key": "sk-u****isuy",
      "base_url": "https://api.siliconflow.cn/v1"
    },
    "qwen": {
      "api_key": "sk-d****5d6f",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    }
  },
  "defaults": {
    "llm": { "provider": "qwen", "model": "qwen-plus-2025-12-01" },
    "embedding": { "provider": "siliconflow", "model": "Qwen/Qwen3-Embedding-8B" },
    "rerank": { "provider": "siliconflow", "model": "Qwen/Qwen3-Reranker-8B" }
  }
}
```

### 8.4 常见问题排查

#### 问题1：模型配置显示不正确（如显示 ollama 而非 siliconflow）

**原因**：租户默认配置未同步或为空

**解决方案**：
1. 前端设置页面点击"同步到服务器"
2. 验证配置已保存：`GET /v1/settings/models`
3. 检查 `defaults` 字段是否有值

#### 问题2：向量维度不匹配错误

```
different vector dimensions 2560 and 1024
```

**原因**：检索时使用的 Embedding 模型与入库时不一致

**解决方案**：
1. 检查知识库配置：`GET /v1/knowledge-bases/{kb_id}`
2. 确保检索时使用相同的 Embedding 模型
3. 如需更换模型，需要重新入库文档

**注意**：pgvector 现已支持**按知识库隔离表**，不同知识库可以使用不同维度的 Embedding 模型：
- 每个知识库独立一张表：`pgvec_kb_{kb_id}`
- 不会出现跨知识库的维度冲突
- 同一知识库内仍需保持 Embedding 模型一致

#### 问题3：LLM 连接失败

```
All connection attempts failed
```

**原因**：LLM 服务不可达（如 Ollama 未启动或网络问题）

**解决方案**：
1. 检查租户默认 LLM 配置是否正确
2. 确保 API Key 有效
3. 检查 base_url 是否可访问

#### 问题4：文档入库时报 API Key 未配置

```
[ERROR] 向量库写入失败: SILICONFLOW_API_KEY 未配置，无法生成真实 Embedding
```

**原因**：文档入库接口未正确获取租户的 Embedding 配置

**解决方案**：
1. 确保在前端设置页面配置了 Embedding 提供商的 API Key
2. 点击"同步到服务器"保存配置
3. 验证配置已保存：`GET /v1/settings/models`
4. 如问题仍存在，检查 `app/api/routes/documents.py` 是否使用了 `model_config_resolver`

**配置优先级（文档入库）**：
```
1. 高级批量入库 API 传入的 embedding_provider/model
   ↓
2. 租户 model_settings 中的 embedding 配置
   ↓
3. 知识库 config 中的 embedding 配置
   ↓
4. 环境变量（EMBEDDING_PROVIDER、SILICONFLOW_API_KEY 等）
```

#### 问题5：文档入库时报 Qdrant 连接失败（使用 pgvector 时）

```
[ERROR] 向量库写入失败: All connection attempts failed
文档 xxx 多后端写入失败: [qdrant] All connection attempts failed
```

**原因**：多后端写入功能默认尝试同时写入 Qdrant，但当前部署未启动 Qdrant 服务

**说明**：
- 主向量库（pgvector）写入**已成功**
- 错误来自 `_maybe_upsert_llamaindex` 的多后端写入逻辑
- 当 `VECTOR_STORE=postgresql` 时，不应再尝试写入 Qdrant

**解决方案**：
1. 确认使用最新代码（已修复此问题）
2. 重启 Docker：`docker compose restart api`
3. 如需同时写入多个向量库，在知识库配置中显式指定：
   ```json
   {
     "ingestion": {
       "store": {
         "type": "milvus",
         "params": { "host": "localhost", "port": 19530 }
       }
     }
   }
   ```

### 8.5 相关代码位置

如需调试或修改配置获取逻辑，参考以下文件：

| 文件 | 说明 |
|------|------|
| `app/services/model_config.py` | `ModelConfigResolver` 配置解析器 |
| `app/api/routes/rag.py` | RAG 接口，获取 LLM/Embedding/Rerank 配置 |
| `app/api/routes/rag_stream.py` | 流式 RAG 接口 |
| `app/api/routes/openai_compat.py` | OpenAI 兼容接口（Chat/Embeddings） |
| `app/api/routes/query.py` | 检索接口，获取 Embedding 配置 |
| `app/api/routes/documents.py` | 文档入库接口，获取 Embedding 配置 |
| `app/services/rag.py` | RAG 生成服务，使用租户 LLM 配置 |
| `app/services/ingestion.py` | 文档摄取服务，使用 Embedding 配置生成向量 |
| `app/schemas/internal.py` | `RAGParams` 内部参数模型定义 |
