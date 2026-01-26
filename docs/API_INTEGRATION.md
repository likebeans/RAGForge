# RAGForge API 对接文档

> **更新时间**: 2026-01-21  
> **测试环境**: http://192.168.168.105:8020

## 概述

RAGForge 提供以下核心 API 接口供 Agent 服务对接：

| 接口 | 路径 | 说明 |
|------|------|------|
| 知识库管理 | `/v1/knowledge-bases` | 创建、查询、删除知识库 |
| 文档管理 | `/v1/knowledge-bases/{kb_id}/documents` | 上传、查询、删除文档 |
| **检索 API** | `/v1/retrieve` | 从知识库检索相关文档片段 |
| **RAG 生成 API** | `/v1/rag` | 结合检索和 LLM 生成回答 |

## 认证

所有 API 请求需要在 Header 中携带 API Key：

```
Authorization: Bearer kb_sk_xxxxxxxxxxxxxxxx
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

```bash
curl -X POST -H "Authorization: Bearer kb_sk_xxx" \
  -F "file=@document.md" \
  "http://192.168.168.105:8020/v1/knowledge-bases/{kb_id}/documents"
```

**支持的文件类型**: `.md`, `.txt`, `.pdf`, `.docx`

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
  "answer": "根据提供的参考资料，针对**关节疼痛**问题，推荐使用：\n\n### ✅ **典恒金崮膏**\n\n**理由如下：**\n- 明确宣称"三效协同直击关节根源"，主打改善关节健康；\n- 适用人群中包含：久坐族、中老年、运动人群、湿寒体质——这些群体常伴有关节不适或疼痛；\n- 组方理念源自"医圣李时珍养生精髓"，严选二十二味道地本草...\n\n⚠️ 注意事项：\n- 不宜与藜芦同用；\n- 忌食高嘌呤食物、海鲜等...",
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

## 3. 错误码说明

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

---

## 4. Python 快速接入代码

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

## 5. 检索器类型

| 检索器 | 说明 | 适用场景 |
|--------|------|---------|
| `dense` | 稠密向量检索 | 语义相似（默认） |
| `bm25` | BM25 稀疏检索 | 精确关键词匹配 |
| `hybrid` | Dense + BM25 混合 | 通用问答（推荐） |
| `hyde` | HyDE（LLM 生成假设文档） | 复杂语义问题 |
| `multi_query` | 多查询扩展 | 提高召回率 |
| `fusion` | 融合检索 + Rerank | 高质量召回 |

---

## 6. 健康检查

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

## 7. 模型配置优先级

RAGForge 的模型配置（Embedding/LLM/Rerank）遵循以下优先级规则：

### 7.1 配置优先级

| 模型类型 | 优先级（从高到低） |
|----------|-------------------|
| **Embedding** | 请求参数 > 知识库配置 > 租户默认配置 > 环境变量 |
| **LLM** | 请求参数 > 租户默认配置 > 环境变量 |
| **Rerank** | 请求参数 > 租户默认配置 > 环境变量 |

### 7.2 配置来源说明

1. **请求参数** (`*_override`)：API 请求中传入的覆盖配置
2. **知识库配置**：创建知识库时指定的 `config.embedding`
3. **租户默认配置**：前端设置页面同步到服务器的 `model_settings.defaults`
4. **环境变量**：Docker 环境变量（如 `EMBEDDING_PROVIDER`、`LLM_PROVIDER`）

### 7.3 查看当前租户配置

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

### 7.4 常见问题排查

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

#### 问题3：LLM 连接失败

```
All connection attempts failed
```

**原因**：LLM 服务不可达（如 Ollama 未启动或网络问题）

**解决方案**：
1. 检查租户默认 LLM 配置是否正确
2. 确保 API Key 有效
3. 检查 base_url 是否可访问

### 7.5 相关代码位置

如需调试或修改配置获取逻辑，参考以下文件：

| 文件 | 说明 |
|------|------|
| `app/services/model_config.py` | `ModelConfigResolver` 配置解析器 |
| `app/api/routes/rag.py` | RAG 接口，获取 LLM/Embedding/Rerank 配置 |
| `app/api/routes/rag_stream.py` | 流式 RAG 接口 |
| `app/api/routes/query.py` | 检索接口，获取 Embedding 配置 |
| `app/services/rag.py` | `_build_response` 构建响应的 model 信息 |
| `app/schemas/internal.py` | `RAGParams` 内部参数模型定义 |
