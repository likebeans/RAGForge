# Self-RAG Pipeline API 设计文档

## 竞品分析

### Dify 知识库 API

| 端点 | 说明 |
|------|------|
| `POST /v1/datasets` | 创建知识库 |
| `GET /v1/datasets` | 列出知识库 |
| `DELETE /v1/datasets/{id}` | 删除知识库 |
| `POST /v1/datasets/{id}/document/create_by_text` | 从文本创建文档 |
| `POST /v1/datasets/{id}/document/create-by-file` | 从文件创建文档 |
| `POST /v1/datasets/{id}/document/update_by_text` | 更新文档（文本） |
| `DELETE /v1/datasets/{id}/documents/{doc_id}` | 删除文档 |
| `GET /v1/datasets/{id}/documents` | 列出文档 |
| `POST /v1/datasets/{id}/documents/{doc_id}/segments` | 添加分段 |
| `GET /v1/datasets/{id}/documents/{doc_id}/segments` | 查询分段 |
| `DELETE /v1/datasets/{id}/segments/{segment_id}` | 删除分段 |
| `POST /v1/datasets/{id}/retrieve` | 检索 |

### RAGFlow 知识库 API

| 端点 | 说明 |
|------|------|
| **数据集管理** |
| `POST /api/v1/datasets` | 创建数据集 |
| `GET /api/v1/datasets` | 列出数据集（支持分页、排序、过滤） |
| `PUT /api/v1/datasets/{id}` | 更新数据集 |
| `DELETE /api/v1/datasets` | 删除数据集（支持批量） |
| **文档管理** |
| `POST /api/v1/datasets/{id}/documents` | 上传文档 |
| `GET /api/v1/datasets/{id}/documents` | 列出文档（支持分页、状态过滤） |
| `PUT /api/v1/datasets/{id}/documents/{doc_id}` | 更新文档 |
| `DELETE /api/v1/datasets/{id}/documents` | 删除文档（支持批量） |
| `GET /api/v1/datasets/{id}/documents/{doc_id}` | 下载文档 |
| `POST /api/v1/datasets/{id}/chunks` | 解析文档（触发切分） |
| `POST /api/v1/datasets/{id}/chunks/stop` | 停止解析 |
| **Chunk 管理** |
| `GET /api/v1/datasets/{id}/documents/{doc_id}/chunks` | 列出 Chunks |
| `POST /api/v1/datasets/{id}/documents/{doc_id}/chunks` | 添加 Chunk |
| `PUT /api/v1/datasets/{id}/chunks/{chunk_id}` | 更新 Chunk |
| `DELETE /api/v1/datasets/{id}/chunks` | 删除 Chunks |
| `POST /api/v1/datasets/{id}/retrieval` | 检索 |
| **高级功能** |
| `POST /api/v1/datasets/{id}/knowledge_graph` | 构建知识图谱 |
| `GET /api/v1/datasets/{id}/knowledge_graph` | 获取知识图谱 |

---

## 接口统一约定

- 认证：`Authorization: Bearer <api_key>`，所有接口除 `/healthz` 外均需携带。
- 内容类型：`application/json`；当前阶段仅支持 JSON 文本上传。
- ID 规范：全部使用 UUID 字符串；文档 ID 全局唯一，服务端会校验所属租户/知识库。
- 时间格式：ISO 8601（UTC）。
- 列表约定：当前响应统一返回 `items` 与 `total`；若需要分页，统一使用 `page`(>=1) 与 `page_size`(<=100) 作为查询参数，响应增加 `page/page_size/pages` 字段。
- 错误响应：`{"detail": "错误信息", "code": "ERROR_CODE"}`，`code` 预留枚举如下。

| code | 场景 |
|------|------|
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

---

## 功能评估

### 必须实现（P0）

| 端点 | 说明 | 理由 |
|------|------|------|
| `GET /v1/knowledge-bases` | 列出知识库 | 基础管理功能，用户需要查看所有知识库 |
| `DELETE /v1/knowledge-bases/{id}` | 删除知识库 | 基础管理功能，清理不需要的知识库 |
| `GET /v1/knowledge-bases/{id}/documents` | 列出文档 | 管理知识库内容的基础功能 |
| `DELETE /v1/documents/{id}` | 删除文档 | 清理文档，向量也需同步删除 |

### 建议实现（P1）

| 端点 | 说明 | 理由 |
|------|------|------|
| `GET /v1/documents/{id}` | 获取文档详情 | 查看文档信息和处理状态 |
| `GET /v1/documents/{id}/chunks` | 列出文档 Chunks | 调试切分效果，查看具体内容 |
| `POST /v1/knowledge-bases/{id}/documents/batch` | 批量上传文档 | 提高效率，减少 API 调用次数 |

### 可选实现（P2）

| 端点 | 说明 | 理由 |
|------|------|------|
| `PUT /v1/documents/{id}` | 更新文档 | 修改文档内容，需重新切分和向量化 |
| `POST /v1/chunks` | 手动添加 Chunk | 精细控制知识内容 |
| `PUT /v1/chunks/{id}` | 更新 Chunk | 修正切分错误 |
| `DELETE /v1/chunks/{id}` | 删除 Chunk | 移除不需要的内容 |
| `GET /v1/knowledge-bases/{id}/stats` | 知识库统计 | 文档数、Chunk 数、Token 数等 |

### 暂不实现

| 功能 | 理由 |
|------|------|
| 知识图谱 | 复杂度高，当前阶段不需要 |
| 文件上传（multipart） | 当前使用 JSON content 方式足够 |
| 批量删除 | 可以循环调用单个删除 |

---

## 设计改进要点（基于评估）

- **检索范围明确**：`POST /v1/retrieve` 必须显式提供 `knowledge_base_ids`，不设默认知识库。跨库检索需 KB 配置允许混合（`query.retriever.allow_mixed=true`），否则必须使用同配置的 KB 列表。
- **检索过滤增强**：支持 `score_threshold` 过滤低分结果，`metadata_filter` 进行元数据精确匹配。
- **摄取与状态可见性**：上传文档立即切分+向量化；Chunk 状态 `pending/indexing/indexed/failed`，失败时返回 `indexing_error`；文档摘要异步生成，`summary_status` 取值 `pending/generating/completed/failed/skipped`。`GET /v1/documents/{id}` 需暴露这些关键信息。
- **资源作用域一致**：文档 ID 全局唯一，但在删除/查询时服务端仍校验租户与知识库，防止误删跨租户/跨库文档。前端无需再传 KB ID 删除。
- **列表参数统一**：请求侧统一 `page/page_size`，响应侧返回 `items/total/page/page_size/pages`。
- **Schema 明确化**：为核心接口补充请求/响应字段说明和示例，避免客户端依赖隐式默认值。
- **扩展留白**：支持 JSON 文本上传，新增 `source_url` 拉取；后续可扩展文件直传/批量上传。

---

## 最终 API 设计

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

### 检索

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/v1/retrieve` | 语义检索 | ✅ 已实现 |

### API Key 管理

| 方法 | 端点 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/v1/api-keys` | 创建 API Key | ✅ 已实现 |
| `GET` | `/v1/api-keys` | 列出 API Keys | ✅ 已实现 |
| `PATCH` | `/v1/api-keys/{id}` | 更新 API Key | ✅ 已实现 |
| `POST` | `/v1/api-keys/{id}/revoke` | 吊销 API Key | ✅ 已实现 |

---

## 响应格式

### 列表响应（当前实现）

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

---

## 关键接口字段与示例

### `POST /v1/retrieve` 语义检索

请求参数：
- `query` (string, required)：查询语句
- `knowledge_base_ids` (string[], required)：目标知识库 ID 列表，必须显式传入
- `top_k` (int, optional, 默认 5，范围 1-50)：返回数量
- `score_threshold` (float, optional, 0-1)：低于该分数的结果将被过滤
- `metadata_filter` (object, optional)：按元数据精确匹配过滤结果

示例请求：
```json
{
  "query": "孕妇可以吃这个药吗",
  "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"],
  "top_k": 3,
  "score_threshold": 0.6,
  "metadata_filter": {"source": "markdown"}
}
```

示例响应（按相似度降序）：
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
  ]
}
```

### `POST /v1/knowledge-bases/{id}/documents` 上传文档

请求参数：
- `title` (string, required)
- `content` (string, conditionally required)：纯文本内容（与 `source_url` 至少提供一个）
- `source_url` (string, optional)：从 URL 拉取文本内容
- `metadata` (object, optional)
- `source` (string, optional)：来源类型，如 `pdf/docx/url/text`

示例请求：
```json
{
  "title": "复方南五加口服液说明书",
  "content": "全文内容...",
  "metadata": {"category": "drug_instruction"},
  "source": "markdown"
}
```

示例响应：
```json
{
  "document_id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
  "chunk_count": 59
}
```

处理语义：
- 创建文档记录，`summary_status=pending`（摘要异步生成，可关闭）。
- 切分内容，Chunk 依次进入 `pending → indexing → indexed/failed`，失败时写入 `indexing_error`。
- 写入向量库与 BM25 索引；如 KB 配置跳过 Qdrant 则仅写 BM25。
- 若提供 `source_url` 将先拉取文本内容再摄取。

### `GET /v1/documents/{id}` 文档详情

返回字段：
- `id`, `title`, `knowledge_base_id`, `source`, `metadata`
- `chunk_count`, `created_at`
- `summary`（可选）、`summary_status`：`pending/generating/completed/failed/skipped`

示例响应：
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

### `GET /v1/documents/{id}/chunks` Chunk 列表

响应字段：
- `items`: `[{"id","document_id","index","text","indexing_status","metadata"}]`
- `total`: int

`indexing_status` 取值：`pending/indexing/indexed/failed`；`metadata` 默认包含 `chunk_index/total_chunks`。

### `GET /v1/knowledge-bases` 列出知识库

请求参数（可扩展分页）：
- `page`，`page_size`（可选，默认 1/20）

响应示例：
```json
{
  "items": [
    {
      "id": "2da0774b-c20e-416e-8e9b-33032db806a7",
      "name": "药品说明书",
      "description": "药品说明书知识库（已更新）",
      "config": {"chunker": "markdown"}
    }
  ],
  "total": 13,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

## 实现计划

### 已完成（P0） ✅

1. `GET /v1/knowledge-bases` - 列出知识库 ✅
2. `DELETE /v1/knowledge-bases/{id}` - 删除知识库 ✅
3. `GET /v1/knowledge-bases/{id}/documents` - 列出文档 ✅
4. `DELETE /v1/documents/{id}` - 删除文档 ✅

### 已完成（P1） ✅

1. `GET /v1/documents/{id}` - 获取文档详情 ✅
2. `GET /v1/documents/{id}/chunks` - 列出 Chunks ✅
3. 列表接口分页与过滤参数对齐（请求/响应增加 `page/page_size`）✅
4. 错误码枚举与返回结构落地 ✅
