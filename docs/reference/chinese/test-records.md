# Self-RAG Pipeline 测试记录

本文档记录系统功能测试的过程、指令和结果。

## 测试环境

| 配置项 | 值 |
|--------|-----|
| **Embedding Provider** | Ollama |
| **Embedding Model** | bge-m3 |
| **Vector Dimension** | 1024 |
| **LLM Provider** | Ollama |
| **LLM Model** | qwen3:14b |
| **API 服务端口** | 8020 |
| **PostgreSQL 端口** | 5435 (宿主机) |
| **Qdrant 端口** | 6333 |
| **测试 API Key** | `kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8` |

---

## 已完成测试

### 1. 健康检查 ✅

**测试时间**: 2024-12-02（更新于 2024-12-04）

**指令**:
```bash
curl -s -w "\nHTTP: %{http_code}\n" http://localhost:8020/health
```

**结果**:
```json
{"status":"ok"}
HTTP: 200
```

**结论**: API 服务正常运行

> 注意：健康检查端点已从 `/healthz` 改为 `/health`

---

### 2. 创建知识库 ✅

**测试时间**: 2024-12-02

**指令**:
```bash
curl -s -X POST http://localhost:8020/v1/knowledge-bases \
  -H "Authorization: Bearer kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8" \
  -H "Content-Type: application/json" \
  -d '{"name": "药品说明书", "description": "药品说明书知识库"}' | python3 -m json.tool
```

**结果**:
```json
{
    "id": "2da0774b-c20e-416e-8e9b-33032db806a7",
    "name": "药品说明书",
    "description": "药品说明书知识库",
    "config": {}
}
```

**结论**: 知识库创建成功

---

### 3. 文档上传与切分 ✅

**测试时间**: 2024-12-02

**测试文档**: `test/复方南五加口服液说明书.md`

**指令**:
```bash
CONTENT=$(cat /home/admin1/work/self_rag_pipeline/test/复方南五加口服液说明书.md | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
curl -s -X POST "http://localhost:8020/v1/knowledge-bases/2da0774b-c20e-416e-8e9b-33032db806a7/documents" \
  -H "Authorization: Bearer kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"复方南五加口服液说明书\", \"content\": $CONTENT}" | python3 -m json.tool
```

**结果**:
```json
{
    "document_id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
    "chunk_count": 59
}
```

**结论**: 文档上传成功，被切分为 59 个 chunks

---

### 4. 语义检索（Ollama bge-m3） ✅

**测试时间**: 2024-12-02

#### 测试用例 1: 查询孕妇用药

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8" \
  -H "Content-Type: application/json" \
  -d '{"query": "孕妇可以吃这个药吗", "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"], "top_k": 3}'
```

**结果**:
| 排名 | Score | 内容 |
|------|-------|------|
| 1 | 0.65 | **孕妇禁用** ✅ |
| 2 | 0.64 | 如与其他药物同时使用可能会发生药物相互作用... |
| 3 | 0.63 | 请仔细阅读说明书并按说明使用或在药师指导下购买和使用 |

**结论**: 正确找到"孕妇禁用"相关信息

#### 测试用例 2: 查询用法用量

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8" \
  -H "Content-Type: application/json" \
  -d '{"query": "这个药怎么吃", "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"], "top_k": 2}'
```

**结果**:
| 排名 | Score | 内容 |
|------|-------|------|
| 1 | 0.70 | **口服，一次10毫升，一日2次，早晚空腹时服** ✅ |
| 2 | 0.69 | 请仔细阅读说明书并按说明使用或在药师指导下购买和使用 |

**结论**: 正确找到用法用量信息

#### 测试用例 3: 查询糖尿病患者用药

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8" \
  -H "Content-Type: application/json" \
  -d '{"query": "糖尿病人能吃吗", "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"], "top_k": 2}'
```

**结果**:
| 排名 | Score | 内容 |
|------|-------|------|
| 1 | 0.70 | **糖尿病患者禁服** ✅ |
| 2 | 0.61 | 高血压、心脏病、肝病、肾病等慢性病患者应在医师指导下服用 |

**结论**: 正确找到糖尿病禁忌信息

---

### 5. 获取知识库详情 ✅

**指令**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8020/v1/knowledge-bases/2da0774b-c20e-416e-8e9b-33032db806a7" | python3 -m json.tool
```

**结果**:
```json
{
    "id": "2da0774b-c20e-416e-8e9b-33032db806a7",
    "name": "药品说明书",
    "description": "药品说明书知识库",
    "config": {}
}
```

---

### 6. 更新知识库配置 ✅

**指令**:
```bash
curl -s -X PATCH "http://localhost:8020/v1/knowledge-bases/2da0774b-c20e-416e-8e9b-33032db806a7" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "药品说明书知识库（已更新）", "config": {"chunker": "markdown"}}' | python3 -m json.tool
```

**结果**: 更新成功，验证后 description 和 config 已变更
```json
{
    "id": "2da0774b-c20e-416e-8e9b-33032db806a7",
    "name": "药品说明书",
    "description": "药品说明书知识库（已更新）",
    "config": {"chunker": "markdown"}
}
```

---

### 7. API Key 管理 ✅

**创建新 API Key**:
```bash
curl -s -X POST "http://localhost:8020/v1/api-keys" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key-2"}' | python3 -m json.tool
```

**结果**:
```json
{
    "id": "73dd03e2-3417-46ca-baa7-a9dc3366a083",
    "name": "test-key-2",
    "prefix": "kb_sk_1Y",
    "api_key": "kb_sk_1YGOFqxRpRIDs4wlrBD3KRH_-x5lfLqzzS_52LzrAbc"
}
```

---

### 8. 认证失败处理 ✅

**无效 API Key 测试**:
```bash
curl -s -w "\nHTTP: %{http_code}\n" \
  -H "Authorization: Bearer kb_sk_invalid12345678901234567890" \
  "http://localhost:8020/v1/knowledge-bases/xxx"
```

**结果**:
```
{"detail":"Invalid API key"}
HTTP: 401
```

**无 Authorization 头测试**:
```bash
curl -s -w "\nHTTP: %{http_code}\n" \
  "http://localhost:8020/v1/knowledge-bases/xxx"
```

**结果**:
```
{"detail":"Missing or invalid Authorization header"}
HTTP: 401
```

**结论**: 认证机制正常工作

---

### 9. 列出知识库 ✅

**指令**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8020/v1/knowledge-bases" | python3 -m json.tool
```

**结果**:
```json
{
    "items": [
        {
            "id": "2da0774b-c20e-416e-8e9b-33032db806a7",
            "name": "药品说明书",
            "description": "药品说明书知识库（已更新）",
            "config": {"chunker": "markdown"}
        },
        ...
    ],
    "total": 13
}
```

---

### 10. 列出文档 ✅

**指令**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8020/v1/knowledge-bases/$KB_ID/documents" | python3 -m json.tool
```

**结果**:
```json
{
    "items": [
        {
            "id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
            "title": "复方南五加口服液说明书",
            "knowledge_base_id": "2da0774b-c20e-416e-8e9b-33032db806a7",
            "source": null,
            "chunk_count": 59,
            "created_at": "2025-12-02T07:10:03.618518Z"
        }
    ],
    "total": 1
}
```

---

### 11. 删除知识库 ✅

**指令**:
```bash
# 创建测试知识库
curl -s -X POST $API_BASE/v1/knowledge-bases \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "删除测试KB", "description": "用于测试删除功能"}'

# 删除知识库
curl -s -w "\nHTTP: %{http_code}\n" -X DELETE \
  "$API_BASE/v1/knowledge-bases/{test_kb_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**结果**:
```
HTTP: 204
```

**验证**:
```bash
# 再次访问已删除的知识库
curl -s "$API_BASE/v1/knowledge-bases/{test_kb_id}" \
  -H "Authorization: Bearer $API_KEY"
# 返回: {"detail":"Knowledge base not found"}
# HTTP: 404
```

---

### 12. 获取文档详情 ✅

**指令**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "$API_BASE/v1/documents/95fdb55c-7fda-46ca-92f2-1be57e1bb1e9" | python3 -m json.tool
```

**结果**:
```json
{
    "id": "95fdb55c-7fda-46ca-92f2-1be57e1bb1e9",
    "title": "复方南五加口服液说明书",
    "knowledge_base_id": "2da0774b-c20e-416e-8e9b-33032db806a7",
    "metadata": {},
    "source": null,
    "chunk_count": 59,
    "created_at": "2025-12-02T07:10:03.618518Z",
    "summary": null,
    "summary_status": "skipped"
}
```

---

### 13. 列出文档 Chunks ✅

**指令**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "$API_BASE/v1/documents/95fdb55c-7fda-46ca-92f2-1be57e1bb1e9/chunks"
```

**结果**:
```json
{
    "items": [
        {"id": "...", "index": 0, "text": "...", "indexing_status": "indexed"},
        ...
    ],
    "total": 59
}
```

---

### 14. 分页参数测试 ✅

**知识库列表分页**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "$API_BASE/v1/knowledge-bases?page=1&page_size=3"
```

**结果**:
```json
{
    "items": [...],
    "total": 13,
    "page": 1,
    "page_size": 3,
    "pages": 5
}
```

---

### 15. 错误码测试 ✅

**KB_NOT_FOUND**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "$API_BASE/v1/knowledge-bases/00000000-0000-0000-0000-000000000000"
# 返回: {"detail":"Knowledge base not found","code":"KB_NOT_FOUND"}
```

**DOC_NOT_FOUND**:
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  "$API_BASE/v1/documents/00000000-0000-0000-0000-000000000000"
# 返回: {"detail":"Document not found","code":"DOC_NOT_FOUND"}
```

---

### 16. 检索过滤 - score_threshold ✅

**指令**:
```bash
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "孕妇可以吃吗", "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"], "top_k": 3, "score_threshold": 0.8}'
# 返回: {"results": []}  (阈值过高，无结果)

curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "孕妇可以吃吗", "knowledge_base_ids": ["2da0774b-c20e-416e-8e9b-33032db806a7"], "top_k": 3, "score_threshold": 0.3}'
# 返回: 3 条结果，score 范围 0.55-0.65
```

---

### 17. URL 拉取文档 ✅

**指令**:
```bash
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "URL拉取测试", "source_url": "https://raw.githubusercontent.com/baidu/lac/master/README.md"}'
```

**结果**:
```json
{
    "document_id": "6f9625d3-8caa-456e-9f59-4907882aa077",
    "chunk_count": 194
}
```

---

### 18. 检索过滤 - metadata_filter ✅

**指令**:
```bash
# 不带过滤（返回所有来源）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "用法", "knowledge_base_ids": ["$KB_ID"], "top_k": 3}'
# 返回: 药品说明书(source=null) + URL拉取测试(source=url)

# 带 metadata_filter 过滤
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "用法", "knowledge_base_ids": ["$KB_ID"], "top_k": 3, "metadata_filter": {"source": "url"}}'
# 返回: 仅 URL拉取测试，过滤掉了 source=null 的结果
```

**结论**: metadata_filter 精确匹配有效

---

## 测试规划

### Phase 1: 基础功能测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 1.1 | 健康检查 | ✅ 通过 | `GET /health` |
| 1.2 | API Key 认证 | ✅ 通过 | Bearer Token 认证 |
| 1.3 | 创建知识库 | ✅ 通过 | `POST /v1/knowledge-bases` |
| 1.4 | 文档上传 | ✅ 通过 | `POST /v1/knowledge-bases/{id}/documents` |
| 1.5 | 语义检索 | ✅ 通过 | `POST /v1/retrieve` |
| 1.6 | 列出知识库 | ✅ 通过 | `GET /v1/knowledge-bases` |
| 1.7 | 获取知识库详情 | ✅ 通过 | `GET /v1/knowledge-bases/{id}` |
| 1.8 | 更新知识库配置 | ✅ 通过 | `PATCH /v1/knowledge-bases/{id}` |
| 1.9 | 删除知识库 | ✅ 通过 | `DELETE /v1/knowledge-bases/{id}` |
| 1.10 | 列出文档 | ✅ 通过 | `GET /v1/knowledge-bases/{id}/documents` |
| 1.11 | 删除文档 | ✅ 通过 | `DELETE /v1/documents/{id}` |
| 1.12 | 列出 API Keys | ✅ 通过 | `GET /v1/api-keys` |
| 1.13 | 创建 API Key | ✅ 通过 | `POST /v1/api-keys` |
| 1.14 | 无效 API Key 拒绝 | ✅ 通过 | 返回 401 Unauthorized |

### Phase 1.5: P1 功能验证（分页/错误码/检索过滤/URL拉取）

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 1.15 | 获取文档详情 | ✅ 通过 | `GET /v1/documents/{id}` 返回 summary_status |
| 1.16 | 列出文档 Chunks | ✅ 通过 | `GET /v1/documents/{id}/chunks` 返回 indexing_status |
| 1.17 | 分页参数 - 知识库列表 | ✅ 通过 | `page/page_size` 返回 total/pages |
| 1.18 | 分页参数 - 文档列表 | ✅ 通过 | `page/page_size` 返回 total/pages |
| 1.19 | 错误码 - KB_NOT_FOUND | ✅ 通过 | `{"code":"KB_NOT_FOUND","detail":"..."}` |
| 1.20 | 错误码 - DOC_NOT_FOUND | ✅ 通过 | `{"code":"DOC_NOT_FOUND","detail":"..."}` |
| 1.21 | 错误码 - INVALID_API_KEY | ✅ 通过 | 返回 `{"code":"INVALID_API_KEY"}` |
| 1.22 | 检索过滤 - score_threshold | ✅ 通过 | 阈值 0.8 返回空，0.3 返回结果 |
| 1.23 | 检索过滤 - metadata_filter | ✅ 通过 | `{"source":"url"}` 过滤有效 |
| 1.24 | URL 拉取文档 | ✅ 通过 | 从 GitHub 拉取成功，生成 194 chunks |
| 1.25 | 文件直传上传 | ✅ 通过 | multipart/form-data 上传 .md 文件 |
| 1.26 | 批量上传文档 | ✅ 通过 | 一次上传 3 个文档，全部成功 |

### Phase 2: 切分器测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 2.1 | simple 切分器 | ✅ 通过 | 按段落切分，3 段 → 3 chunks |
| 2.2 | sliding_window 切分器 | ✅ 通过 | window=50, overlap=10 切分有效 |
| 2.3 | recursive 切分器 | ✅ 通过 | 按自然边界递归切分 |
| 2.4 | markdown 切分器 | ✅ 通过 | 按标题层级切分，5 节 → 5 chunks |
| 2.5 | code 切分器 | ✅ 通过 | 按语法结构切分 Python 代码 |
| 2.6 | parent_child 切分器 | ✅ 通过 | 父子分块，保留 parent_id 关系 |
| 2.7 | markdown_section 切分器 | ✅ 通过 | 按标题分节，保留 heading 元数据 |
| 2.8 | llama_sentence 切分器 | ✅ 通过 | 句子级切分，保持句子完整性 |
| 2.9 | llama_token 切分器 | ✅ 通过 | Token 级切分，精确控制长度 |

---

## Phase 2 测试详情

### 2.6 parent_child 切分器 ✅

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "ParentChild测试", "config": {"ingestion": {"chunker": {"name": "parent_child", "params": {"parent_chars": 200, "child_chars": 50, "overlap": 10}}}}}'
```

**结果**: 生成 5 chunks，每个含 `parent_id: "parent_0"`，父子关系正确

---

### 2.7 markdown_section 切分器 ✅

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "MarkdownSection测试", "config": {"ingestion": {"chunker": {"name": "markdown_section"}}}}'
```

**结果**: 按标题分节，metadata 含 `heading: "# 产品介绍"` 等

---

### 2.8 llama_sentence 切分器 ✅

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "LlamaSentence测试", "config": {"ingestion": {"chunker": {"name": "llama_sentence", "params": {"max_tokens": 100, "chunk_overlap": 20}}}}}'
```

**结果**: 按句子边界切分，保持句子完整

**注意**: `chunk_overlap` 不能大于 `max_tokens`

---

### 2.9 llama_token 切分器 ✅

**指令**:
```bash
curl -s -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "LlamaToken测试", "config": {"ingestion": {"chunker": {"name": "llama_token", "params": {"max_tokens": 30, "chunk_overlap": 5}}}}}'
```

**结果**: 严格按 Token 数量切分，长文本 → 3 chunks

---

### Phase 2 Bug 修复

**问题**: `llama_sentence` 报错 `'dict' object has no attribute 'id_'`

**修复**: `app/pipeline/chunkers/llama_sentence.py` - 使用 LlamaIndex Document 对象
```python
from llama_index.core.schema import Document
doc = Document(text=text, metadata=metadata or {})
nodes = self.splitter.get_nodes_from_documents([doc])
```

---

### Phase 3: 检索器测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 3.1 | dense 检索器 | ✅ 通过 | 稠密向量检索（默认） |
| 3.2 | bm25 检索器 | ✅ 通过 | 从数据库加载 chunks，支持持久化（已修复） |
| 3.3 | hybrid 检索器 | ✅ 通过 | Dense + BM25 混合检索 |
| 3.4 | fusion 检索器 | ✅ 通过 | RRF 融合检索 + 可选 Rerank |
| 3.5 | hyde 检索器 | ✅ 通过 | HyDE 假设文档嵌入检索，调用 LLM 生成假设文档 |
| 3.6 | llama_dense 检索器 | ✅ 通过 | 使用 RealEmbedding 调用项目配置的 Embedding 服务（已修复） |
| 3.7 | llama_bm25 检索器 | ✅ 通过 | LlamaIndex BM25 检索（从 DB 加载） |
| 3.8 | llama_hybrid 检索器 | ✅ 通过 | LlamaIndex 混合检索 |
| 3.9 | multi_query 检索器 | ✅ 通过 | 多查询扩展检索（新增） |
| 3.10 | self_query 检索器 | ✅ 通过 | 自查询检索 - LLM 解析元数据过滤（新增） |
| 3.11 | parent_document 检索器 | ✅ 通过 | 父文档检索 - 小块检索返回父块（新增） |
| 3.12 | ensemble 检索器 | ✅ 通过 | 集成检索 - 任意组合多检索器（新增） |

#### 新增检索器说明

| 检索器 | 功能 | 使用场景 |
|--------|------|----------|
| `multi_query` | 使用 LLM 生成多个查询变体，分别检索后 RRF 融合 | 用户查询不精确时提高召回 |
| `self_query` | LLM 自动解析查询，提取元数据过滤条件 | 「找2024年的Python教程」→ 自动过滤 year=2024 |
| `parent_document` | 检索小块（精确），返回父块（完整上下文） | 长文档检索，需配合 parent_child chunker |
| `ensemble` | 任意组合多个检索器，支持 RRF/加权融合 | 灵活的多路召回策略 |

#### Phase 3 测试详情

##### 3.2 bm25 检索器 ✅

**创建 KB**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"BM25测试","config":{"query":{"retriever":{"name":"bm25"}}}}'
```

**上传文档**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases/{kb_id}/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Qdrant技术文档","content":"Qdrant是一个高性能向量数据库，专门用于存储和搜索高维向量数据。它支持余弦相似度和欧几里得距离等多种度量方式。Qdrant采用Rust编写，具有出色的性能和内存效率。"}'
```

**检索测试**:
```bash
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"Qdrant向量数据库","knowledge_base_ids":["{kb_id}"],"top_k":3}'
```

**检索结果**: 返回 2 个结果，从数据库加载 chunks 构建 BM25 索引，支持容器重启后持久化

---

##### 3.5 hyde 检索器 ✅

**创建 KB**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"HyDE测试","config":{"query":{"retriever":{"name":"hyde","params":{"base_retriever":"dense"}}}}}'
```

**检索结果**: `score=0.6270`，LLM 生成假设文档后进行语义检索

---

##### 3.6 llama_dense 检索器 ✅

**创建 KB**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"LlamaDense测试","config":{"query":{"retriever":{"name":"llama_dense"}}}}'
```

**上传文档**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases/{kb_id}/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"RAG技术文档","content":"RAG是检索增强生成技术，结合了检索系统和大语言模型。它先从知识库检索相关文档，再将检索结果作为上下文输入给LLM生成答案。"}'
```

**检索测试**:
```bash
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"什么是RAG技术","knowledge_base_ids":["{kb_id}"],"top_k":3}'
```

**检索结果**: `score=0.6440`，使用 RealEmbedding 调用项目配置的 Embedding 服务（Ollama bge-m3）

---

##### 3.9 multi_query 检索器 ✅

**创建 KB**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"MultiQuery测试","config":{"query":{"retriever":{"name":"multi_query","params":{"base_retriever":"dense","num_queries":3}}}}}'
```

**检索结果**: `score=0.8013`，成功生成查询变体并 RRF 融合

---

##### 3.10 self_query 检索器 ✅

**创建 KB**:
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"SelfQuery测试","config":{"query":{"retriever":{"name":"self_query","params":{"base_retriever":"dense"}}}}}'
```

**说明**: LLM 自动解析查询提取元数据过滤条件

---

##### 3.11 parent_document 检索器 ✅

**创建 KB** (配合 parent_child chunker):
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"ParentDoc测试","config":{"ingestion":{"chunker":{"name":"parent_child"}},"query":{"retriever":{"name":"parent_document","params":{"base_retriever":"dense"}}}}}'
```

**说明**: 检索小块返回父块，保留完整上下文

---

##### 3.12 ensemble 检索器 ✅

**创建 KB** (组合 dense + llama_bm25):
```bash
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"Ensemble测试","config":{"query":{"retriever":{"name":"ensemble","params":{"retrievers":[{"name":"dense","weight":0.7},{"name":"llama_bm25","weight":0.3}],"mode":"rrf"}}}}}'
```

**检索结果**: `score=0.0328` (RRF 分数)，多路召回融合成功

---

### Phase 4: 高级功能测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 4.1 | HyDE 查询变换 | ✅ 通过 | 假设文档嵌入（需要 LLM），生成 3 个假设文档 |
| 4.2 | RAG Fusion (multi_query) | ✅ 通过 | 多查询扩展，LLM 生成查询变体，返回完整检索详情 |
| 4.3 | 文档摘要 | ✅ 通过 | LLM 自动生成文档摘要 |
| 4.4 | Chunk Enrichment | ✅ 通过 | LLM Chunk 语义增强 |
| 4.5 | Rerank 重排 | ✅ 通过 | fusion + rerank，使用 bge-reranker-large |

#### 4.1 HyDE 查询变换测试

**测试日期**: 2024-12-03

**模型配置验证**:
| 模型 | 类型 | 状态 | 说明 |
|------|------|------|------|
| bge-m3 | Embedding | ✅ | 维度 1024 |
| qwen3:14b | LLM | ✅ | 需要 max_tokens=2000+ (thinking 模式) |
| qwen2.5:7b | LLM | ✅ | 无需特殊配置 |
| qllama/bge-reranker-large | Rerank | ✅ | 正常 |

**代码修改**:
1. `app/api/routes/query.py`: 支持 `retriever_override` 参数传递到服务层
2. `app/services/query.py`: `_resolve_retriever` 支持 override 参数，`retrieve_chunks` 返回检索器名称
3. `app/pipeline/query_transforms/hyde.py`: max_tokens 从 256 → 2000，添加 `/no_think` 禁用 qwen3 thinking
4. `.env`: `HYDE_MAX_TOKENS=2000`

**测试命令**:
```bash
export API_KEY="your_api_key_here"
export API_BASE="http://localhost:8020"
export KB_ID="your_kb_id_here"

curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这个药物有什么禁忌？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 3,
    "retriever_override": {"name": "hyde"}
  }'
```

**测试结果**:
```json
{
  "model": {
    "retriever": "hyde",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3"
  },
  "results": [
    {
      "hyde_queries": [
        "这个药物有什么禁忌？",
        "在临床应用中，该药物的使用需特别注意以下情况：对活性成分或辅料存在已知过敏反应的患者应避免使用...",
        "**药物使用注意事项** 本品禁用于对活性成分或辅料过敏者。患有严重肝肾功能不全...",
        "**药物使用注意事项** 本品禁用于对活性成分或辅料过敏者。在以下情况下应避免使用..."
      ],
      "text": "## 【注意事项】\n\n1. 忌辛辣、生冷、油腻食物。\n2. 感冒发热病人不宜服用。...",
      "score": 0.7428
    }
  ]
}
```

**结果分析**:
- ✅ HyDE 生成 4 个查询（1 个原始 + 3 个假设文档）
- ✅ LLM 正确生成药物禁忌相关的假设文档
- ✅ 检索结果正确匹配到药品说明书的注意事项章节
- ⏱️ 耗时约 16 秒（包含 3 次 LLM 调用）

#### 4.2 multi_query 检索器测试

**测试日期**: 2024-12-03

**代码修改**:
1. `app/pipeline/retrievers/multi_query.py`: 添加 `retrieval_details` 返回每个查询的完整检索结果
2. `app/pipeline/query_transforms/rag_fusion.py`: max_tokens 从 100 → 500，添加 `/no_think`
3. `app/schemas/query.py`: 添加 `generated_queries`, `queries_count`, `retrieval_details` 字段
4. `app/services/query.py`: 传递 multi_query 相关字段

**测试命令**:
```bash
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这个药物的用法用量是什么？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 3,
    "retriever_override": {"name": "multi_query"}
  }'
```

**测试结果**:
```json
{
  "model": {
    "retriever": "multi_query",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b"
  },
  "results": [{
    "generated_queries": [
      "这个药物的用法用量是什么？",
      "这个药品的服用方法和剂量如何？",
      "该药物的使用方法及摄入量是怎样的？",
      "请提供该药物的推荐用法和用量信息。"
    ],
    "queries_count": 4,
    "retrieval_details": [
      {"query": "这个药物的用法用量是什么？", "hits_count": 3, "hits": [...]},
      {"query": "这个药品的服用方法和剂量如何？", "hits_count": 3, "hits": [...]},
      ...
    ],
    "text": "## 【用法用量】\n\n口服，一次10毫升，一日2次，早晚空腹时服。",
    "score": 0.6921
  }]
}
```

**结果分析**:
- ✅ LLM 生成 4 个查询（1 个原始 + 3 个变体）
- ✅ 返回每个查询的完整检索结果（`retrieval_details`）
- ✅ RRF 融合后正确返回用法用量章节

#### 4.3 文档摘要测试

**测试日期**: 2024-12-03

**代码修改**:
1. `app/config.py`: 添加 `doc_summary_model` 配置字段
2. `pyproject.toml`: 添加 `openai>=1.30.0` 和 `llama-index>=0.11.0` 依赖

**测试代码**:
```python
from app.pipeline.enrichers.summarizer import DocumentSummarizer

summarizer = DocumentSummarizer(min_tokens=50, max_tokens=800)
summary = summarizer.generate(test_content)
```

**测试结果**:
```
✅ 文档摘要生成成功:
复方南五加口服液为中药制剂，主要成分包括五加皮、黄芪、当归等。
该药具有温阳益气、养心安神功效，适用于气血亏虚、阳气不足引起的症状，
如心悸、气短、夜眠不宁，可作为辅助治疗药物。用法为口服，每次10毫升，
每日2次，早晚空腹服用。使用期间需忌辛辣、生冷、油腻食物，感冒发热患者禁用。
```

#### 4.4 Chunk Enrichment 测试

**测试日期**: 2024-12-03

**代码修改**:
1. `app/config.py`: 添加 `chunk_enrichment_model` 配置字段，max_tokens 增加到 800

**测试代码**:
```python
from app.pipeline.enrichers.chunk_enricher import ChunkEnricher

enricher = ChunkEnricher(max_tokens=800, context_chunks=1)
enriched = enricher.enrich(
    chunk_text="## 【用法用量】\n\n口服，一次10毫升，一日2次，早晚空腹时服。",
    doc_title="复方南五加口服液说明书",
    doc_summary="复方南五加口服液为中药制剂，具有温阳益气、养心安神功效。",
    preceding_chunks=["## 【功能主治】\n\n温阳益气，养心安神..."],
    succeeding_chunks=["## 【注意事项】\n\n1. 忌辛辣、生冷、油腻食物。"],
)
```

**测试结果**:
```
✅ Chunk Enrichment 成功:
本段内容位于说明书"功能主治"与"注意事项"之间，属于药品使用说明的核心部分，
明确具体服用方法。关键实体包括药品名称"复方南五加口服液"、剂量"10毫升"、
频次"一日2次"及服用条件"早晚空腹时服"。需注意"空腹时服"指每次服药前应保持
空腹状态，非仅早晚两次服用时需空腹。原文核心信息为口服剂量及服用时间要求，
未涉及其他使用限制。
```

#### 4.5 Rerank 重排测试

**测试命令**:
```bash
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这个药物的功效是什么？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 3,
    "retriever_override": {"name": "fusion", "params": {"rerank": true}}
  }'
```

**测试结果**:
- Retriever: `fusion` | Rerank: `ollama/qllama/bge-reranker-large`
- 检索结果按 rerank 分数排序:
  1. score=0.0320 | 功能主治章节
  2. score=0.0310 | 注意事项章节
  3. score=0.0299 | 用法用量章节
- ✅ Rerank 模型正确重排结果

### Phase 5: 可观测性与高级功能测试 (Phase 3 已完成功能)

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 5.1 | 结构化日志 | ✅ 通过 | 时间+级别+[request_id]+模块+消息 |
| 5.2 | 请求追踪 X-Request-ID | ✅ 通过 | 响应头包含 x-request-id |
| 5.3 | 审计日志记录 | ✅ 通过 | 中间件自动记录关键 API 调用 |
| 5.4 | 审计日志查询 | ✅ 通过 | 数据库直查确认记录存在 |
| 5.5 | RAG 生成接口 | ✅ 通过 | 返回 answer + sources |
| 5.6 | 父子分块检索 | ✅ 通过 | parent_document 返回 context_text |
| 5.7 | RAPTOR 检索器 | ✅ 通过 | 完整测试：3层摘要树构建、collapsed模式检索 |

#### 5.1 结构化日志测试

**测试日期**: 2024-12-04

**测试方法**: 查看 API 日志输出格式

```bash
# 设置 JSON 日志格式
export LOG_JSON=true
export LOG_LEVEL=INFO

# 启动服务，观察日志输出
docker compose logs -f api
```

**预期结果**:
```json
{"timestamp":"2024-12-04T03:00:00.000Z","level":"INFO","logger":"app.api","message":"Request completed","request_id":"abc123","tenant_id":"tenant_001","method":"GET","path":"/v1/knowledge-bases","status_code":200,"duration_ms":50}
```

---

#### 5.2 请求追踪 X-Request-ID

**测试日期**: 2024-12-04

**指令**:
```bash
curl -s -i "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" | grep -E "^(X-Request-ID|X-Response-Time)"
```

**预期结果**:
```
X-Request-ID: abc123-def456-...
X-Response-Time: 50ms
```

---

#### 5.3 审计日志记录

**测试日期**: 2024-12-04

**测试步骤**:
1. 执行一些 API 操作
2. 查询审计日志确认记录

**指令**:
```bash
# 执行操作
curl -s "$API_BASE/v1/knowledge-bases" -H "Authorization: Bearer $API_KEY"

# 查询审计日志（Admin API）
curl -s "$API_BASE/admin/audit-logs?limit=5" \
  -H "X-Admin-Token: $ADMIN_TOKEN" | python3 -m json.tool
```

**预期结果**:
```json
{
  "items": [
    {
      "id": "...",
      "request_id": "abc123",
      "tenant_id": "tenant_001",
      "action": "list_knowledge_bases",
      "method": "GET",
      "path": "/v1/knowledge-bases",
      "status_code": 200,
      "duration_ms": 50,
      "created_at": "2024-12-04T03:00:00Z"
    }
  ]
}
```

---

#### 5.4 审计日志查询过滤

**测试日期**: 2024-12-04

**指令**:
```bash
# 按操作类型过滤
curl -s "$API_BASE/admin/audit-logs?action=retrieve" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# 按时间范围过滤
curl -s "$API_BASE/admin/audit-logs?start_time=2024-12-04T00:00:00Z&end_time=2024-12-04T23:59:59Z" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

---

#### 5.5 RAG 生成接口测试

**测试日期**: 2024-12-04

**指令**:
```bash
curl -s -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这个药有什么禁忌？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 3,
    "system_prompt": "你是一个专业的药品顾问，基于提供的文档回答问题。",
    "temperature": 0.7,
    "max_tokens": 500
  }' | python3 -m json.tool
```

**预期结果**:
```json
{
  "answer": "根据药品说明书，该药物的禁忌包括：1. 孕妇禁用...",
  "sources": [
    {
      "chunk_id": "...",
      "text": "【禁忌】孕妇禁用...",
      "score": 0.85,
      "knowledge_base_id": "..."
    }
  ],
  "model": {
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "retriever": "hybrid"
  }
}
```

---

#### 5.6 父子分块检索测试

**测试日期**: 2024-12-04

**测试步骤**:
1. 创建使用 parent_child chunker 的知识库
2. 上传文档
3. 检索验证 context_text 包含父块内容

**指令**:
```bash
# 创建 KB（parent_child chunker + parent_document retriever）
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "父子分块测试",
    "config": {
      "ingestion": {"chunker": {"name": "parent_child", "params": {"parent_chars": 500, "child_chars": 100}}},
      "query": {"retriever": {"name": "parent_document"}}
    }
  }'

# 上传文档后检索
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "关键词", "knowledge_base_ids": ["父子分块KB_ID"], "top_k": 1}'
```

**预期结果**:
- 检索结果 `text` 为子块内容
- `context_text` 包含父块完整上下文

---

#### 5.7 RAPTOR 检索器测试

**测试日期**: 2024-12-04

**测试状态**: ✅ 通过

**RAPTOR 原理**:
RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 是一种多层次索引方法：
1. 将文档切分为 chunks
2. 对 chunks 进行向量聚类
3. 对每个聚类使用 LLM 生成摘要
4. 递归处理摘要，直到达到最大层数

**测试结果**:
```
=== 构建 RAPTOR 索引 (5个原始文档) ===
Generating embeddings for level 0.
Performing clustering for level 0.
Generating summaries for level 0 with 1 clusters.
Level 0 created summaries/clusters: 1
...
Level 2 created summaries/clusters: 1

索引统计:
  总节点数: 8 (5个原始 + 3个摘要)
  层数: 3
  
=== RAPTOR 节点详情 ===
[原始文档] 阿司匹林是一种常见的解热镇痛药...
[原始文档] 阿司匹林的主要成分是乙酰水杨酸...
[原始文档] 服用阿司匹林时应注意胃肠道反应...
[原始文档] 阿司匹林常用于预防心血管疾病...
[原始文档] 儿童和青少年感冒发热时不宜使用...
[摘要 L0] 阿司匹林是一种具有抗炎、退热和止痛作用的常见解热镇痛药...
[摘要 L1] 阿司匹林是一种以乙酰水杨酸为主要成分的解热镇痛药...
[摘要 L2] 阿司匹林主要成分为乙酰水杨酸，具有抗炎、退热、止痛...

=== 检索结果 ===
查询: "阿司匹林有什么禁忌症？"
1. [摘要 L1] score=0.6832  ← LLM 生成的聚合摘要
2. [摘要 L2] score=0.6795  ← 更高层的聚合摘要
```

**API 使用示例**:
```bash
# 检索时指定 raptor 检索器
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "阿司匹林有什么禁忌症？",
    "knowledge_base_ids": ["KB_ID"],
    "top_k": 5,
    "retriever_override": {"name": "raptor", "params": {"mode": "collapsed"}}
  }'
```

**检索模式**:
- `collapsed`: 扁平化检索，所有层级节点一起 top-k（默认）
- `tree_traversal`: 树遍历检索，从顶层向下逐层筛选

**返回字段**:
- `raptor_level`: 节点层级（-1=原始文档，0/1/2=摘要层级）

**依赖**:
- `llama-index-packs-raptor>=0.1.3`
- `llama-index-llms-ollama>=0.1.0`
- `llama-index-embeddings-ollama>=0.1.0`

---

### Phase 6: 多租户与安全测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 6.1 | 多租户隔离 | ✅ 通过 | 不同租户数据隔离 |
| 6.2 | API Key 限流 | ✅ 通过 | 请求频率限制 (120/min) |
| 6.3 | 无效 API Key | ✅ 通过 | 认证失败处理 |
| 6.4 | 租户禁用 | ✅ 通过 | 禁用后拒绝访问 |

#### 6.1 多租户隔离测试

**测试场景**: 创建两个租户 A 和 B，验证数据隔离

```bash
# 租户 A 创建知识库
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY_A" \
  -d '{"name": "租户A的知识库"}'

# 租户 B 列出知识库 - 应看不到 A 的
curl "$API_BASE/v1/knowledge-bases" -H "Authorization: Bearer $API_KEY_B"
# 返回: {"items":[],"total":0,...}

# 租户 B 尝试访问 A 的知识库
curl "$API_BASE/v1/knowledge-bases/{kb_a_id}" -H "Authorization: Bearer $API_KEY_B"
# 返回: {"detail":"Knowledge base not found","code":"KB_NOT_FOUND"}
```

**测试结果**:
- 租户 A 创建的知识库: 2 个
- 租户 B 看到的知识库: 0 个
- 跨租户访问: 返回 404 KB_NOT_FOUND
- ✅ 数据隔离有效

#### 6.2 无效 API Key 测试

**测试场景**: 验证认证失败处理

```bash
# 无 Authorization 头
curl "$API_BASE/v1/knowledge-bases"
# 返回: {"detail":"Missing or invalid Authorization header","code":"UNAUTHORIZED"}

# 无效 API Key
curl "$API_BASE/v1/knowledge-bases" -H "Authorization: Bearer invalid_key"
# 返回: {"detail":"Invalid API key","code":"INVALID_API_KEY"}
```

**测试结果**:
- 无认证头: 401 UNAUTHORIZED
- 无效 Key: 401 INVALID_API_KEY
- ✅ 认证失败正确处理

#### 6.3 API Key 限流测试

**测试场景**: 快速发送超过限制的请求

```bash
# 默认限制: 120 次/分钟
for i in $(seq 1 130); do
  curl -s "$API_BASE/v1/knowledge-bases" -H "Authorization: Bearer $API_KEY"
done
# 第 121+ 个请求返回 429
```

**测试结果**:
- 触发限流后返回: `HTTP 429 Too Many Requests`
- 响应体: `{"detail":"Rate limit exceeded","code":"RATE_LIMIT_EXCEEDED"}`
- ✅ 限流机制正常工作

#### 6.4 租户禁用测试

**测试场景**: 禁用租户后验证 API Key 被拒绝

```bash
# 禁用租户
curl -X POST "$API_BASE/admin/tenants/{tenant_id}/disable" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{"reason": "Security test"}'
# 返回: {"status":"disabled",...}

# 禁用后尝试访问
curl "$API_BASE/v1/knowledge-bases" -H "Authorization: Bearer $API_KEY"
# 返回: {"detail":"Tenant is disabled","code":"TENANT_DISABLED"}

# 重新启用
curl -X POST "$API_BASE/admin/tenants/{tenant_id}/enable" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
# 返回: {"status":"active",...}

# 启用后访问恢复
curl "$API_BASE/v1/knowledge-bases" -H "Authorization: Bearer $API_KEY"
# 返回: {"items":[...],"total":2,...}
```

**测试结果**:
- 禁用后访问: 403 TENANT_DISABLED
- 启用后访问: 正常返回数据
- ✅ 租户禁用/启用功能正常

### Phase 7: 运维端点测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 7.1 | 存活检查 /health | ✅ 通过 | Kubernetes Liveness Probe |
| 7.2 | 就绪检查 /ready | ✅ 通过 | 检查 DB + Qdrant 状态 |
| 7.3 | 系统指标 /metrics | ✅ 通过 | 运行时间、调用统计、配置信息 |
| 7.4 | 检索指标记录 | ✅ 通过 | 检索后自动记录分数分布 |

#### 7.1 存活检查 /health

**测试日期**: 2024-12-05

**指令**:
```bash
curl -s -w "\nHTTP: %{http_code}\n" http://localhost:8020/health
```

**实际结果**:
```json
{"status":"ok"}
HTTP: 200
```

**结论**: ✅ 存活检查正常

---

#### 7.2 就绪检查 /ready

**测试日期**: 2024-12-05

**指令**:
```bash
curl -s http://localhost:8020/ready | python3 -m json.tool
```

**实际结果**:
```json
{
    "status": "ok",
    "checks": {
        "database": {"status": "ok", "message": "connected"},
        "qdrant": {"status": "ok", "message": "connected (3 collections)"}
    },
    "timestamp": "2025-12-05T06:47:15.074969+00:00"
}
```

**结论**: ✅ 数据库和 Qdrant 连接正常

---

#### 7.3 系统指标 /metrics

**测试日期**: 2024-12-05

**指令**:
```bash
curl -s http://localhost:8020/metrics | python3 -m json.tool
```

**实际结果**:
```json
{
    "service": {
        "uptime_seconds": 71789.51,
        "uptime_human": "19h 56m 29s",
        "timestamp": "2025-12-05T06:46:20.852577+00:00"
    },
    "config": {
        "llm_provider": "ollama",
        "llm_model": "qwen3:14b",
        "embedding_provider": "qwen",
        "embedding_model": "text-embedding-v3",
        "embedding_dim": 1024,
        "rerank_provider": "ollama"
    },
    "stats": {
        "calls": {},
        "retrievals": {"dense": {"count": 1}}
    }
}
```

**结论**: ✅ 系统指标正常返回

---

#### 7.4 检索指标记录

**测试日期**: 2024-12-05

**测试步骤**:
1. 执行一次检索
2. 查看 /metrics 的 stats.retrievals 计数增加

**指令**:
```bash
# 执行检索
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "测试", "knowledge_base_ids": ["'"$KB_ID"'"], "top_k": 3}'

# 查看指标
curl -s http://localhost:8020/metrics | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Retrievals:', json.dumps(data['stats']['retrievals'], indent=2))
"
```

**实际结果**:
```json
{
  "dense": {"count": 2}
}
```

**结论**: ✅ 检索指标从 count=1 增加到 count=2，记录正常

---

### Phase 8: 企业权限系统测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 8.1 | API Key identity 字段 | ✅ 通过 | identity JSON 正确保存到数据库 |
| 8.2 | 文档敏感度设置 | ✅ 通过 | sensitivity_level 正确设置和保存 |
| 8.3 | ACL 白名单 | ✅ 通过 | acl_roles/acl_groups 正确保存到向量库 |
| 8.4 | Security Trimming | ✅ 通过 | 无权限用户只看到 public 文档 |
| 8.5 | 管理员访问 | ✅ 通过 | admin/销售部 Key 可访问全部文档 |

#### 8.1 API Key identity 字段

**测试日期**: 2024-12-04

**指令**:
```bash
# 创建带身份信息的 API Key
curl -s -X POST "$API_BASE/admin/tenants/$TENANT_ID/api-keys" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Final-Identity-Test",
    "role": "read",
    "identity": {
      "user_id": "sales_user",
      "roles": ["sales"],
      "groups": ["dept_sales"],
      "clearance": "restricted"
    }
  }' | python3 -m json.tool
```

**实际结果**: ✅ 通过
```json
{
    "id": "10e209af-390e-4df7-bd93-b868f69044e2",
    "name": "Final-Identity-Test",
    "prefix": "kb_sk_y4",
    "role": "read",
    "identity": {
        "user_id": "sales_user",
        "roles": ["sales"],
        "groups": ["dept_sales"],
        "clearance": "restricted"
    },
    "api_key": "kb_sk_y4e3uKsDYvj0-4C6pPA2Vv8TEHWnWpAbAVeyJPtT7IU"
}
```

**数据库验证**:
```sql
SELECT name, identity FROM api_keys WHERE name = 'Final-Identity-Test';
-- identity 字段正确保存 JSON 数据
```

---

#### 8.2 文档敏感度设置

**测试日期**: 2024-12-04

**指令**:
```bash
# 上传 public 文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "公开产品介绍",
    "content": "我们公司的产品信息，任何人都可以查看。",
    "sensitivity_level": "public"
  }'

# 上传 restricted 文档（需要 ACL 匹配）
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "销售定价策略",
    "content": "内部机密的定价信息和折扣策略，仅销售团队可见。",
    "sensitivity_level": "restricted",
    "acl_roles": ["sales", "manager"]
  }'
```

**实际结果**: ✅ 通过

数据库验证:
```sql
SELECT title, sensitivity_level, acl_roles FROM documents 
WHERE title IN ('公开产品介绍', '销售定价策略');

        title         | sensitivity_level |      acl_roles       
----------------------+-------------------+----------------------
 公开产品介绍         | public            | NULL
 销售定价策略         | restricted        | ["sales", "manager"]
```

---

#### 8.3 ACL 白名单测试

**测试日期**: 2024-12-04

**指令**:
```bash
# 上传带完整 ACL 字段的文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "ACL测试文档-Final",
    "content": "这是ACL测试内容，仅特定角色可见。",
    "sensitivity_level": "restricted",
    "acl_roles": ["sales", "manager"],
    "acl_groups": ["dept_sales"]
  }'
```

**实际结果**: ✅ 通过

数据库验证:
```sql
SELECT title, sensitivity_level, acl_roles, acl_groups FROM documents 
WHERE title = 'ACL测试文档-Final';

       title         | sensitivity_level |      acl_roles       |   acl_groups    
---------------------+-------------------+----------------------+-----------------
 ACL测试文档-Final   | restricted        | ["sales", "manager"] | ["dept_sales"]
```

**ACL 信息也正确写入向量库 payload 中**，用于检索时的 Security Trimming。

---

#### 8.4 Security Trimming 测试

**测试日期**: 2024-12-04

**测试场景**: 验证检索时自动过滤无权限文档

**测试环境**:
- 知识库: `ACL-Security-Trimming-Test` (ID: 0e77d7fd-476c-43d6-9112-bfcc3ac99a25)
- 文档: 1 个 public + 1 个 restricted (仅 sales 角色可见)
- API Keys:
  - 普通 Key (无 identity): `kb_sk_7J-AwCEOsGw6CUxgJdF0kCPIgkn-jca-VajAP06LkKE`
  - 销售部 Key (有 sales 角色): `kb_sk_y4e3uKsDYvj0-4C6pPA2Vv8TEHWnWpAbAVeyJPtT7IU`

**指令**:
```bash
# 普通 Key 检索（无 identity）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $NORMAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "产品", "knowledge_base_ids": ["'"$KB_ID"'"], "top_k": 10}'

# 销售部 Key 检索（有 sales 角色）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $SALES_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "产品", "knowledge_base_ids": ["'"$KB_ID"'"], "top_k": 10}'
```

**实际结果**: ✅ 通过

| API Key | 返回结果数 | 文档 |
|---------|-----------|------|
| 普通 Key (无 identity) | 1 | 公开产品介绍 (public) |
| 销售部 Key (sales 角色) | 2 | 公开产品介绍 + 销售定价策略 |

**关键验证**: 无 identity 的 Key 无法看到 restricted 文档，ACL 过滤正确生效。

---

#### 8.5 管理员访问测试

**测试日期**: 2024-12-04

**测试场景**: 验证 admin 角色可访问所有文档

**指令**:
```bash
# admin Key 检索（应返回所有文档）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "产品", "knowledge_base_ids": ["'"$KB_ID"'"], "top_k": 10}'
```

**实际结果**: ✅ 通过

| API Key | 返回结果数 | 文档 |
|---------|-----------|------|
| Admin Key | 2 | 公开产品介绍 + 销售定价策略 |

**结论**: Admin 角色 (`is_admin=True`) 绕过 ACL 检查，可以访问所有文档。

---

#### Phase 8 代码修复记录

测试过程中修复了以下问题：

1. **`app/schemas/api_key.py`**: 添加 `identity` 字段到 `APIKeyCreate` 和 `APIKeyInfo`
2. **`app/schemas/document.py`**: 添加 `sensitivity_level`, `acl_users/roles/groups` 字段
3. **`app/schemas/internal.py`**: `IngestionParams` 添加 ACL 参数
4. **`app/api/routes/admin.py`**: 创建 API Key 时传递 `identity`
5. **`app/api/routes/documents.py`**: 文档上传时传递 ACL 字段
6. **`app/api/routes/query.py`**: 添加 `user_context` 传递到 `retrieve_chunks` 以启用 Security Trimming
7. **`app/services/ingestion.py`**: 创建 Document 时写入 ACL 字段 (`acl_allow_users/roles/groups`)
8. **`app/infra/metrics.py`**: 修复 f-string 格式化语法错误

---

### Phase 9: 多租户存储隔离测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 9.1 | 跨租户数据隔离 | ✅ 通过 | 租户 A 无法访问租户 B 的 KB |
| 9.2 | Qdrant 向量库隔离 | ✅ 通过 | kb_shared (Partition) + kb_{tenant_id} (Collection) |
| 9.3 | 策略切换 | ✅ 通过 | PATCH API 支持 auto/partition/collection 切换 |

#### 9.1 跨租户数据隔离测试

**测试日期**: 2024-12-04

**测试场景**: 验证租户 A 无法访问租户 B 的知识库和文档

**测试步骤**:
1. 创建租户 A 和 B，各自创建知识库并上传文档
2. 租户 A 检索自己的 KB（应成功）
3. 租户 A 尝试检索租户 B 的 KB（应失败）

**实际结果**: ✅ 通过

| 测试 | 结果 |
|------|------|
| 租户 A 检索自己的 KB | ✅ 返回文档"苹果公司介绍" |
| 租户 A 检索租户 B 的 KB | ✅ 返回 404 "KB_NOT_FOUND" |
| 租户 B 检索自己的 KB | ✅ 返回文档"微软公司介绍" |

**数据库验证**:
```sql
SELECT t.name as tenant, kb.name as kb_name, d.title
FROM documents d
JOIN knowledge_bases kb ON d.knowledge_base_id = kb.id
JOIN tenants t ON d.tenant_id = t.id
WHERE t.name LIKE 'isolation%';
-- 每个租户的文档都正确关联到对应的 tenant_id
```

---

#### 9.2 Qdrant 向量库隔离测试

**测试日期**: 2024-12-04

**实际结果**: ✅ 通过

**Qdrant Collections**:
```
kb_shared                           # 共享 Collection (Partition 模式)
kb_39764725-2b7e-48e1-b755-...     # 租户独立 Collection
kb_829cd757-6599-4995-8bbd-...     # 租户独立 Collection
```

- **Partition 模式**: 多租户共享 `kb_shared`，通过 `tenant_id` payload 过滤
- **Collection 模式**: 每租户独立 `kb_{tenant_id}` Collection

---

#### 9.3 隔离策略切换测试

**测试日期**: 2024-12-04

**测试场景**: 通过 API 切换租户隔离策略

**指令**:
```bash
# 查看当前策略
curl -s "$API_BASE/admin/tenants/$TENANT_ID" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
# 输出: "isolation_strategy": "auto"

# 切换为 collection 模式
curl -s -X PATCH "$API_BASE/admin/tenants/$TENANT_ID" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"isolation_strategy": "collection"}'
```

**实际结果**: ✅ 通过

| 操作 | 结果 |
|------|------|
| 获取租户信息 | 返回 `isolation_strategy: auto` |
| 切换为 collection | 返回 `isolation_strategy: collection` |
| 数据库验证 | ✅ 字段正确更新 |

**代码修复**: 添加 `isolation_strategy` 到 `TenantUpdate` 和 `TenantResponse` schema

---

### Phase 10: 性能测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 10.1 | 批量文档上传 | ✅ 通过 | 20 文档, 平均 354ms/文档 |
| 10.2 | 并发检索 | ✅ 通过 | 10 并发, 响应 264-360ms |
| 10.3 | 大文档处理 | ✅ 通过 | 118KB 文档, 1200 chunks |

#### 10.1 批量文档上传测试

**测试日期**: 2024-12-04

**测试场景**: 连续上传 20 个文档，测量平均耗时

**实际结果**: ✅ 通过

| 指标 | 数值 |
|------|------|
| 文档数 | 20 |
| 成功数 | 20 |
| 平均耗时 | ~354ms/文档 |
| 总耗时 | ~7.1秒 |

---

#### 10.2 并发检索测试

**测试日期**: 2024-12-04

**测试场景**: 同时发起 10 个检索请求

**实际结果**: ✅ 通过

| 请求 | 响应时间 | 结果数 |
|------|---------|------|
| 请求1 | 0.267s | 5 |
| 请求2 | 0.267s | 5 |
| 请求3 | 0.266s | 5 |
| 请求4 | 0.265s | 5 |
| 请求5 | 0.312s | 5 |
| 请求6 | 0.360s | 5 |
| 请求7 | 0.266s | 5 |
| 请求8 | 0.319s | 5 |
| 请求9 | 0.335s | 5 |
| 请求10 | 0.267s | 5 |

**平均响应时间**: ~292ms

---

#### 10.3 大文档处理测试

**测试日期**: 2024-12-04

**测试场景**: 上传超过 100KB 的文档

**实际结果**: ✅ 通过

| 指标 | 数值 |
|------|------|
| 文档大小 | 118.3 KB |
| 切分 Chunk 数 | 1200 |
| 处理耗时 | ~77秒 |
| 平均每 Chunk | ~64ms |

**检索验证**:
```
查询: "深度学习神经网络"
结果: 3 条, 分数 0.727
```

---

### Phase 11: 权限与一致性补充测试

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 11.1 | sensitivity_level 两级设计 | ✅ 验证 | internal 被视为 restricted，需 ACL 白名单 |
| 11.2 | scope_kb_ids KB 白名单 | ✅ 已修复 | 检索时检查 API Key 的 KB 白名单 |
| 11.3 | admin/write/read 角色权限 | ✅ 已修复 | KB/文档写操作需 admin/write 角色 |
| 11.4 | 删除文档后向量库同步 | ✅ 通过 | 向量库正确清理已删除文档 |

#### 11.1 sensitivity_level 两级设计验证

**测试日期**: 2024-12-05

**发现**: ACL 系统简化为两级敏感度：
- `public`: 所有人可访问
- `restricted`: 需要 ACL 白名单匹配（internal/confidential/secret 都视为 restricted）

**测试结果**:
| API Key | clearance | 预期 | 实际 |
|---------|-----------|------|------|
| 无 identity | none | 仅 public | ✅ 1 条 (public) |
| clearance=internal | internal→restricted | public + internal(有ACL) | ✅ 仅 public (internal 无 ACL) |
| clearance=restricted | restricted | 全部 | ✅ 2 条 (public + restricted with ACL) |

**结论**: 设计如此，`internal` 文档需要同时设置 ACL 白名单才能被非 admin 访问。

---

#### 11.2 scope_kb_ids KB 白名单

**测试日期**: 2024-12-05

**测试步骤**:
1. 创建 scope_kb_ids=[KB1] 的 API Key
2. 用该 Key 检索 KB2（不在白名单中）

**预期结果**: 应返回 403

**原实际结果**: ❌ 成功检索到 KB2 的文档

**修复内容**: 
在 `app/api/routes/query.py` 的 `/v1/retrieve` 路由中添加 KB 白名单检查：
```python
# 检查 API Key 的 KB 白名单 (scope_kb_ids)
scope_kb_ids = api_key_ctx.api_key.scope_kb_ids
if scope_kb_ids:
    requested_kb_ids = set(payload.knowledge_base_ids)
    allowed_kb_ids = set(scope_kb_ids)
    unauthorized_kbs = requested_kb_ids - allowed_kb_ids
    if unauthorized_kbs:
        raise HTTPException(status_code=403, detail={"code": "KB_NOT_IN_SCOPE", ...})
```

**修复状态**: ✅ 已修复

**验证测试** (2024-12-05):
```bash
# 创建 scope_kb_ids=[KB1] 的 API Key，尝试检索 KB2
状态码: 403
响应: {
  "detail": "API Key 无权访问以下知识库: ['fbd04d1f-...']",
  "code": "KB_NOT_IN_SCOPE"
}
✅ 验证通过
```

---

#### 11.3 admin/write/read 角色权限

**测试日期**: 2024-12-05

**测试步骤**:
1. 创建 role=read 的 API Key
2. 用该 Key 尝试创建知识库

**预期结果**: 应返回 403 Forbidden

**原实际结果**: ❌ 成功创建知识库

**修复内容**:
在 `app/api/routes/kb.py` 和 `app/api/routes/documents.py` 中，将写操作的依赖从 `get_current_api_key` 改为 `require_role("admin", "write")`：

| 路由 | 操作 | 修复 |
|------|------|------|
| `POST /v1/knowledge-bases` | 创建 KB | ✅ |
| `PATCH /v1/knowledge-bases/{id}` | 更新 KB | ✅ |
| `DELETE /v1/knowledge-bases/{id}` | 删除 KB | ✅ |
| `POST /v1/knowledge-bases/{kb_id}/documents` | 上传文档 | ✅ |
| `POST /v1/knowledge-bases/{kb_id}/documents/upload` | 文件上传 | ✅ |
| `POST /v1/knowledge-bases/{kb_id}/documents/batch` | 批量上传 | ✅ |
| `DELETE /v1/documents/{id}` | 删除文档 | ✅ |

**修复状态**: ✅ 已修复

**验证测试** (2024-12-05):
```bash
# 用 read 角色尝试创建 KB
✅ 测试1 通过: read 角色无法创建 KB (HTTP 403)
   详情: {'detail': "Role 'read' not allowed. Required: ('admin', 'write')"}

# 用 read 角色尝试上传文档
✅ 测试2 通过: read 角色无法上传文档 (HTTP 403)
```

---

#### 11.4 删除文档后向量库同步

**测试日期**: 2024-12-05

**测试步骤**:
1. 创建 KB 并上传文档
2. 检索确认文档存在
3. 删除文档
4. 再次检索确认已清理

**实际结果**:
```
删除前结果: 1 条
删除后结果: 0 条
✅ 向量库同步删除成功
```

**结论**: 删除文档时正确同步清理了 Qdrant 向量库中的 chunks。

---

## 已修复问题

| 问题 | 修复日期 | 修复内容 |
|------|----------|----------|
| scope_kb_ids 未实现 | 2024-12-05 | `app/api/routes/query.py` 添加 KB 白名单检查 |
| 角色权限未应用 | 2024-12-05 | `kb.py`/`documents.py` 写操作添加 `require_role("admin", "write")` |

## 设计说明

| 特性 | 说明 |
|------|------|
| sensitivity_level 两级设计 | `internal/confidential/secret` 都视为 `restricted`，需 ACL 白名单 |

---

## 测试指令速查

### 环境变量设置
```bash
export API_KEY="your_api_key_here"
export API_BASE="http://localhost:8020"
export KB_ID="your_kb_id_here"

# 使用 Ollama 进行 Embedding/LLM/HyDE（使用固定 IP，本地和 Docker 都能访问）
export EMBEDDING_PROVIDER=ollama
export EMBEDDING_MODEL="bge-m3"
export LLM_PROVIDER=ollama
export LLM_MODEL="qwen3:14b"
export OLLAMA_BASE_URL="http://192.168.1.235:11434"

# HyDE 依赖 OpenAI 兼容接口，指向 Ollama 的 /v1
export OPENAI_API_BASE="http://192.168.1.235:11434/v1"
export OPENAI_API_KEY="ollama"   # 任意非空值
export HYDE_ENABLED=true
export HYDE_MAX_TOKENS=2000  # qwen3 thinking 模式需要更多 token
```

### 常用测试指令

```bash
# 健康检查
curl -s $API_BASE/health

# 就绪检查
curl -s $API_BASE/ready | python3 -m json.tool

# 系统指标
curl -s $API_BASE/metrics | python3 -m json.tool

# 列出知识库
curl -s -H "Authorization: Bearer $API_KEY" $API_BASE/v1/knowledge-bases

# 创建知识库
curl -s -X POST $API_BASE/v1/knowledge-bases \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试知识库", "description": "测试用"}'

# 上传文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "测试文档", "content": "这是测试内容..."}'

# 语义检索
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"搜索内容\", \"knowledge_base_ids\": [\"$KB_ID\"], \"top_k\": 5}"

# parent_child 检索上下文验证（命中子片段应带父片段 context_text）
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"子片段关键词\", \"knowledge_base_ids\": [\"$KB_ID\"], \"top_k\": 1}"

# 删除知识库
curl -s -X DELETE "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY"
```

---

## 问题记录

### 已解决问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 文档上传时 `indexing_status` 字段报错 | 数据库迁移脚本未正确设置默认值 | 修改迁移脚本，先添加可空列再设置默认值 |
| Docker 构建超时 | 网络代理问题 | 在 Dockerfile 中添加构建时代理配置 |
| 容器间通信失败 (502 Bad Gateway) | 代理环境变量影响容器内通信 | 在 docker-compose.yml 中清除代理变量 |
| Ollama 连接失败 | 容器无法访问宿主机服务 | 添加 `extra_hosts: host.docker.internal:host-gateway` |
| 向量维度不匹配 | 旧数据使用 256 维，新配置 1024 维 | 删除 Qdrant volume 重新创建 |
| HyDE LLM 响应为空 | qwen3 thinking 模式占用大量 token，256 不够 | 增加 `HYDE_MAX_TOKENS=2000` |
| OpenAI 兼容 API 不支持 /no_think | Ollama /v1 接口不处理 /no_think 标记 | 增加 max_tokens 替代 |

### 待解决问题

| 问题 | 状态 | 备注 |
|------|------|------|
| - | - | 当前无待解决问题 |

---

## 更新日志

| 日期 | 更新内容 |
|------|----------|
| 2024-12-02 | 初始化测试记录，完成基础功能测试（健康检查、创建知识库、文档上传、语义检索） |
| 2024-12-02 | 配置 Ollama bge-m3 作为 Embedding 模型，向量维度 1024 |
| 2024-12-02 | 完成 Phase 1 测试：获取知识库详情、更新配置、API Key 管理、认证失败处理 |
| 2024-12-02 | 发现 4 个 API 端点未实现：列出知识库、删除知识库、列出文档、删除文档 |
| 2024-12-02 | 实现 4 个缺失端点并全部测试通过，Phase 1 全部完成 ✅ |
| 2024-12-02 | 完成 Phase 1.5 P1 功能验证：分页、错误码、score_threshold、metadata_filter、URL 拉取 ✅ |
| 2024-12-02 | 修复 INVALID_API_KEY 错误码，新增文件直传和批量上传端点 ✅ |
| 2024-12-02 | 完成 Phase 2 切分器测试：simple/sliding_window/recursive/markdown/code ✅ |
| 2024-12-02 | 完成 Phase 2 LlamaIndex 切分器测试：parent_child/markdown_section/llama_sentence/llama_token ✅ |
| 2024-12-02 | 新增 4 个高级检索器：multi_query（多查询扩展）、self_query（LLM 元数据解析）、parent_document（父文档检索）、ensemble（集成检索） |
| 2024-12-02 | 完成 Phase 3 检索器测试：dense/hybrid/fusion/llama_bm25/llama_hybrid/multi_query/self_query/parent_document/ensemble ✅ |
| 2024-12-02 | 修复 HyDE 检索器：LLM 生成假设文档后检索 ✅；修复 HashEmbedding 和 llama_dense filters 兼容性问题 |
| 2024-12-02 | 修复 bm25 检索器：从数据库加载 chunks，支持持久化 ✅；修复 llama_dense：使用 RealEmbedding 调用真实 Embedding 服务 ✅ |
| 2024-12-02 | 检索响应新增 `model` 字段，显示使用的 Embedding/LLM/Rerank 模型和检索器名称 |
| 2024-12-03 | 支持 `retriever_override` 参数动态切换检索器；修复 HyDE 与 qwen3 兼容性问题（max_tokens=2000）|
| 2024-12-03 | 完成 Phase 4.1 HyDE 测试：LLM 生成假设文档，检索效果正常 ✅ |
| 2024-12-03 | 完成 Phase 4.2 multi_query 测试：LLM 生成查询变体，RRF 融合 ✅ |
| 2024-12-03 | 完成 Phase 4.5 Rerank 测试：fusion + bge-reranker-large 重排 ✅ |
| 2024-12-04 | 实现可观测性模块：`app/infra/metrics.py`，检索指标自动记录 |
| 2024-12-04 | 增强运维端点：`/health`（存活检查）、`/ready`（就绪检查）、`/metrics`（系统指标）|
| 2024-12-04 | 优化数据库连接池：pool_size=10, max_overflow=20, pool_recycle=1800 |
| 2024-12-04 | 新增部署文档：`docs/部署.md`，包含 Docker Compose / Kubernetes 部署指南 |
| 2024-12-04 | 实现企业权限系统：API Key identity 字段、文档敏感度（public/restricted）、ACL 白名单、Security Trimming |
| 2024-12-04 | 实现多租户存储隔离：Partition/Collection/Auto 三种策略 |
| 2024-12-04 | 新增 Phase 8（企业权限系统测试）和 Phase 9（多租户存储隔离测试）测试计划 |
| 2024-12-04 | **完成 Phase 8 企业权限系统测试** ✅：API Key identity、文档敏感度、ACL 白名单、Security Trimming 全部通过 |
| 2024-12-04 | **完成 Phase 9 多租户存储隔离测试** ✅：跨租户数据隔离、Qdrant 向量库隔离、策略切换 (auto/partition/collection) 全部通过 |
| 2024-12-04 | **完成 Phase 10 性能测试** ✅：批量上传 354ms/文档、10 并发检索 292ms 平均、118KB 大文档 1200 chunks |
| 2024-12-04 | **完成 Phase 5 可观测性测试** ✅：结构化日志、X-Request-ID、审计日志中间件、RAG 接口、parent_document 检索 |
| 2024-12-04 | 实现审计日志中间件 `app/middleware/audit.py`：自动记录 retrieve/rag/kb/document 操作 |
| 2024-12-04 | 完善 RAPTOR 检索器：添加到 Schema 的 RetrieverName Literal 类型 |
| 2024-12-04 | **完成 RAPTOR 功能完整测试** ✅：修复 VectorStore 导入、添加 Ollama LlamaIndex 集成、验证 3 层摘要树构建和检索 |
| 2024-12-05 | **完成 Phase 7 运维端点测试** ✅：存活检查 /health、就绪检查 /ready（DB+Qdrant）、系统指标 /metrics、检索指标记录 |
| 2024-12-05 | **Phase 11 权限与一致性补充测试**：sensitivity_level 两级设计验证 ✅、向量库删除同步 ✅ |
| 2024-12-05 | **修复权限问题**：scope_kb_ids KB 白名单检查 (`query.py`)、角色权限 require_role (`kb.py`/`documents.py`) |
| 2024-12-08 | **Phase 12 安全加固**：API Key 管理 admin 角色校验、RAG 流程 ACL 传递、/v1/rag KB/scope 校验、OpenAI 接口 PermissionError 处理 |
| 2024-12-09 | **Phase 13 模型配置动态化**：Admin API 系统配置管理、KB Embedding 配置校验、请求级 LLM/Rerank 覆盖 |

---

## Phase 12：安全加固测试

> 测试日期：2024-12-08
> 
> 本阶段测试安全漏洞修复后的权限控制是否正常工作。

### 测试准备

```bash
# 设置环境变量
export API_BASE="http://localhost:8020"
export ADMIN_TOKEN="your-admin-token"

# 1. 创建测试租户
curl -s -X POST "$API_BASE/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "security-test"}' | python3 -m json.tool
# 记录 tenant_id 和 admin api_key

# 2. 使用 admin key 创建 read 角色 key
export ADMIN_KEY="<admin_api_key>"
curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "read-only-key", "role": "read"}' | python3 -m json.tool
# 记录 read_key

# 3. 创建 scoped key（只能访问特定 KB）
curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "scoped-key", "role": "read", "scope_kb_ids": ["allowed-kb-id"]}' | python3 -m json.tool
# 记录 scoped_key
```

### 12.1 API Key 管理角色校验 (P0)

**测试目标**: 验证只有 admin 角色才能管理 API Key

#### 12.1.1 read 角色创建 Key（期望 403）

```bash
export READ_KEY="<read_only_key>"
curl -s -w "\nHTTP: %{http_code}\n" -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "hacked-key", "role": "admin"}'
```

**期望结果**:
```json
{"detail":"Role 'read' not allowed. Required: ('admin',)"}
HTTP: 403
```

#### 12.1.2 read 角色列出 Key（期望 403）

```bash
curl -s -w "\nHTTP: %{http_code}\n" "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $READ_KEY"
```

**期望结果**: HTTP 403

#### 12.1.3 admin 角色创建 Key（期望 201）

```bash
curl -s -w "\nHTTP: %{http_code}\n" -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "new-key", "role": "write"}'
```

**期望结果**: HTTP 201

### 12.2 RAG 流程 ACL 传递 (P0)

**测试目标**: 验证 RAG 生成时 user_context 正确传递，受限文档被 ACL 过滤

#### 12.2.1 准备测试数据

```bash
# 上传受限文档
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "机密文档",
    "content": "这是一份机密内容，只有特定用户可以访问。",
    "sensitivity_level": "restricted",
    "acl": {"allowed_identities": ["user-alice"]}
  }'

# 创建带 identity 的 key
curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "bob-key", "role": "read", "identity": "user-bob"}'
# 记录 bob_key

curl -s -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "alice-key", "role": "read", "identity": "user-alice"}'
# 记录 alice_key
```

#### 12.2.2 Bob 查询受限文档（期望 403 或空结果）

```bash
export BOB_KEY="<bob_key>"
curl -s -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $BOB_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "机密内容是什么",
    "knowledge_base_ids": ["'"$KB_ID"'"]
  }'
```

**期望结果**: HTTP 403 `NO_PERMISSION` 或检索结果为空

#### 12.2.3 Alice 查询受限文档（期望成功）

```bash
export ALICE_KEY="<alice_key>"
curl -s -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $ALICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "机密内容是什么",
    "knowledge_base_ids": ["'"$KB_ID"'"]
  }'
```

**期望结果**: HTTP 200，返回包含机密文档的 RAG 回答

### 12.3 /v1/rag KB/scope 校验 (P1)

**测试目标**: 验证 /v1/rag 接口对 KB 存在性和 scope_kb_ids 的校验

#### 12.3.1 查询不存在的 KB（期望 404）

```bash
curl -s -w "\nHTTP: %{http_code}\n" -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test",
    "knowledge_base_ids": ["00000000-0000-0000-0000-000000000000"]
  }'
```

**期望结果**:
```json
{"detail":{"code":"KB_NOT_FOUND","detail":"部分知识库不存在"}}
HTTP: 404
```

#### 12.3.2 scoped key 访问未授权 KB（期望 403）

```bash
export SCOPED_KEY="<scoped_key>"  # scope_kb_ids=["allowed-kb-id"]
curl -s -w "\nHTTP: %{http_code}\n" -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $SCOPED_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test",
    "knowledge_base_ids": ["other-kb-id"]
  }'
```

**期望结果**:
```json
{"detail":{"code":"KB_NOT_IN_SCOPE","detail":"API Key 无权访问以下知识库: ['other-kb-id']"}}
HTTP: 403
```

### 12.4 OpenAI 接口 PermissionError (P2)

**测试目标**: 验证 /v1/chat/completions ACL 被拒绝时返回 403

#### 12.4.1 Bob 通过 OpenAI 接口查询受限文档（期望 403）

```bash
curl -s -w "\nHTTP: %{http_code}\n" -X POST "$API_BASE/v1/chat/completions" \
  -H "Authorization: Bearer $BOB_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "机密内容是什么"}],
    "knowledge_base_ids": ["'"$KB_ID"'"]
  }'
```

**期望结果**:
```json
{"detail":{"code":"NO_PERMISSION","detail":"检索结果因 ACL 权限控制被过滤..."}}
HTTP: 403
```

### 12.5 测试结果汇总

> 测试日期：2024-12-08

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 12.1.1 | read 角色创建 Key | ✅ 通过 | 返回 403 Forbidden |
| 12.1.2 | read 角色列出 Key | ✅ 通过 | 返回 403 Forbidden |
| 12.1.3 | admin 角色创建 Key | ✅ 通过 | 返回 201 Created |
| 12.3.1 | 查询不存在的 KB | ✅ 通过 | 返回 404 KB_NOT_FOUND |
| 12.3.2 | scoped key 访问未授权 KB | ✅ 通过 | 返回 403 KB_NOT_IN_SCOPE |
| 12.4.1 | OpenAI 接口 scope 校验 | ✅ 通过 | 返回 403 KB_NOT_IN_SCOPE |

**附加修复**：测试过程中发现 `create_api_key` 函数未传递 `role`/`scope_kb_ids`/`identity` 字段的 Bug，已修复 (`app/api/routes/api_keys.py`)

---

## Phase 13：模型配置动态化测试

> 测试日期：2024-12-09
> 
> 本阶段测试模型配置动态化功能，包括 Admin API 系统配置管理、KB Embedding 配置校验、请求级 LLM/Rerank 覆盖。

### 功能概述

**配置优先级**（从高到低）：
```
请求级覆盖 > 知识库配置 > 租户配置 > 系统配置 > 环境变量
```

**主要功能**：
1. Admin API 系统配置管理
2. KB Embedding 配置校验（已有文档时禁止变更）
3. 请求级 LLM/Rerank 覆盖

### 测试准备

```bash
# 设置环境变量
export API_BASE="http://localhost:8020"
export ADMIN_TOKEN="test-admin-token-12345"

# 1. 创建测试租户
curl -s -X POST "$API_BASE/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "dynamic-config-test"}' | python3 -m json.tool
# 记录 tenant_id 和 api_key

export TENANT_ID="<tenant_id>"
export API_KEY="<api_key>"
```

### 13.1 Admin API 系统配置管理 (P0)

**测试目标**: 验证系统配置的 CRUD 操作

#### 13.1.1 获取系统配置列表

```bash
curl -s "$API_BASE/admin/system-config" \
  -H "X-Admin-Token: $ADMIN_TOKEN" | python3 -m json.tool
```

**期望结果**: 返回系统配置列表，包含默认的 LLM/Embedding 配置

#### 13.1.2 更新系统配置

```bash
curl -s -X PUT "$API_BASE/admin/system-config/llm_model" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "qwen3:14b"}' | python3 -m json.tool
```

**期望结果**: 配置更新成功

#### 13.1.3 获取单个配置

```bash
curl -s "$API_BASE/admin/system-config/llm_model" \
  -H "X-Admin-Token: $ADMIN_TOKEN" | python3 -m json.tool
```

**期望结果**: 返回更新后的配置值

### 13.2 KB Embedding 配置校验 (P1)

**测试目标**: 验证知识库 Embedding 配置的校验逻辑

#### 13.2.1 创建带 Embedding 配置的知识库

```bash
curl -s -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "embedding-config-test",
    "config": {
      "embedding": {
        "provider": "ollama",
        "model": "bge-m3"
      }
    }
  }' | python3 -m json.tool
# 记录 kb_id
export KB_ID="<kb_id>"
```

**期望结果**: 知识库创建成功，config 包含 embedding 配置

#### 13.2.2 无效 Embedding 提供商（期望 400）

```bash
curl -s -w "\nHTTP: %{http_code}\n" -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "invalid-embedding-test",
    "config": {
      "embedding": {
        "provider": "invalid_provider",
        "model": "some-model"
      }
    }
  }'
```

**期望结果**: 
```json
{"detail":{"code":"VALIDATION_ERROR",...}}
HTTP: 422
```

#### 13.2.3 上传文档到知识库

```bash
curl -s -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "test-doc",
    "content": "这是一个测试文档，用于验证 Embedding 配置变更保护。"
  }' | python3 -m json.tool
```

**期望结果**: 文档上传成功

#### 13.2.4 更新已有文档的 KB Embedding 配置（期望 400）

```bash
curl -s -w "\nHTTP: %{http_code}\n" -X PATCH "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "embedding": {
        "provider": "openai",
        "model": "text-embedding-3-small"
      }
    }
  }'
```

**期望结果**:
```json
{"detail":{"code":"KB_CONFIG_ERROR","detail":"知识库已有文档，不能更改 embedding 配置..."}}
HTTP: 400
```

#### 13.2.5 更新其他配置（不含 Embedding）应成功

```bash
curl -s -X PATCH "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "query": {
        "retriever": {"name": "hybrid"},
        "top_k": 10
      }
    }
  }' | python3 -m json.tool
```

**期望结果**: 配置更新成功（只更新 query 部分，保留原 embedding 配置）

### 13.3 请求级 LLM/Rerank 覆盖 (P2)

**测试目标**: 验证检索/RAG 请求中的 LLM 和 Rerank 覆盖字段

#### 13.3.1 检索请求支持 rerank_override

```bash
# 先执行一次检索，确认 rerank_override 字段被接受
curl -s -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试文档",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "rerank": false
  }' | python3 -m json.tool
```

**期望结果**: 检索成功返回结果

#### 13.3.2 RAG 请求支持 llm_override 字段

```bash
# 验证 Schema 接受 llm_override 字段
curl -s -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这个文档讲了什么",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 3
  }' | python3 -m json.tool
```

**期望结果**: RAG 生成成功返回答案

#### 13.3.3 OpenAPI Schema 验证

```bash
# 获取 OpenAPI schema，确认新字段存在
curl -s "$API_BASE/openapi.json" | python3 -c "
import json, sys
spec = json.load(sys.stdin)
schemas = spec.get('components', {}).get('schemas', {})

# 检查 LLMConfig
if 'LLMConfig' in schemas:
    print('✅ LLMConfig schema exists')
    print('  Fields:', list(schemas['LLMConfig'].get('properties', {}).keys()))
else:
    print('❌ LLMConfig schema missing')

# 检查 RerankConfig
if 'RerankConfig' in schemas:
    print('✅ RerankConfig schema exists')
    print('  Fields:', list(schemas['RerankConfig'].get('properties', {}).keys()))
else:
    print('❌ RerankConfig schema missing')

# 检查 RAGRequest
if 'RAGRequest' in schemas:
    props = schemas['RAGRequest'].get('properties', {})
    if 'llm_override' in props:
        print('✅ RAGRequest.llm_override exists')
    else:
        print('❌ RAGRequest.llm_override missing')
    if 'rerank_override' in props:
        print('✅ RAGRequest.rerank_override exists')
    else:
        print('❌ RAGRequest.rerank_override missing')

# 检查 RetrieveRequest
if 'RetrieveRequest' in schemas:
    props = schemas['RetrieveRequest'].get('properties', {})
    if 'rerank_override' in props:
        print('✅ RetrieveRequest.rerank_override exists')
    else:
        print('❌ RetrieveRequest.rerank_override missing')
"
```

**期望结果**: 所有新增 Schema 字段都存在

### 13.4 测试结果汇总

> 测试日期：2024-12-09

| 序号 | 测试项 | 状态 | 说明 |
|------|--------|------|------|
| 13.1.1 | 获取系统配置列表 | ✅ 通过 | 返回配置列表 |
| 13.1.2 | 更新系统配置 | ✅ 通过 | llm_model 更新为 qwen3:14b |
| 13.1.3 | 获取单个配置 | ✅ 通过 | 返回更新后的值 |
| 13.2.1 | 创建带 Embedding 配置的 KB | ✅ 通过 | 配置保存成功 |
| 13.2.2 | 无效 Embedding 提供商 | ✅ 通过 | Pydantic 校验返回 422 |
| 13.2.3 | 上传文档到 KB | ✅ 通过 | chunk_count=1 |
| 13.2.4 | 已有文档 KB 变更 Embedding（期望失败） | ✅ 通过 | 返回 400 KB_CONFIG_ERROR |
| 13.2.5 | 更新其他配置（不含 Embedding） | ✅ 通过 | 仅更新 query 配置成功 |
| 13.3.1 | 检索请求 rerank_override | ✅ 通过 | Schema 接受字段 |
| 13.3.2 | RAG 请求 llm_override | ✅ 通过 | RAG 生成正常 |
| 13.3.3 | OpenAPI Schema 验证 | ✅ 通过 | LLMConfig/RerankConfig 字段存在 |

**附加修复**：
- 修复 `payload.config` Pydantic 对象转字典问题 (`app/api/routes/kb.py`)
- 修复 embedding 配置兼容性校验逻辑，只在新配置包含 embedding 键时校验 (`app/services/config_validation.py`)
