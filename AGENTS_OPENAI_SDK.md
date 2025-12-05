# OpenAI 兼容接口与 Python SDK

## OpenAI 兼容 API

### 1. Embeddings API

完全兼容 OpenAI Embeddings API 格式。

**端点**: `POST /v1/embeddings`

**请求示例**:
```bash
curl -X POST http://localhost:8020/v1/embeddings \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "测试文本",
    "model": "text-embedding-v3"
  }'
```

**响应格式**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.1, 0.2, ...],
      "index": 0
    }
  ],
  "model": "text-embedding-v3",
  "usage": {
    "prompt_tokens": 3,
    "total_tokens": 3
  }
}
```

### 2. Chat Completions API (RAG 模式)

完全兼容 OpenAI Chat Completions API，通过 `knowledge_base_ids` 参数启用 RAG。

**端点**: `POST /v1/chat/completions`

**请求示例**:
```bash
curl -X POST http://localhost:8020/v1/chat/completions \
  -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "你是一个技术助手"},
      {"role": "user", "content": "Python 有什么应用？"}
    ],
    "model": "gpt-4",
    "knowledge_base_ids": ["kb_id_1"],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

**响应格式**:
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Python 广泛应用于..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  },
  "sources": [
    {
      "chunk_id": "xxx",
      "text": "检索到的文本...",
      "score": 0.85,
      "knowledge_base_id": "kb_id",
      "metadata": {}
    }
  ]
}
```

**重要说明**:
- `model` 参数仅用于兼容性，实际使用的是服务端配置的 LLM（`.env` 中的 `LLM_PROVIDER` 和 `LLM_MODEL`）
- `knowledge_base_ids` 为必填参数，用于启用 RAG 模式
- `sources` 是扩展字段，包含检索到的知识库来源

---

## Python SDK

### 安装

```bash
# 从项目根目录安装
pip install -e ./sdk

# 或使用 uv
uv pip install -e ./sdk
```

### 快速开始

```python
from kb_service_sdk import KBServiceClient

# 初始化客户端
client = KBServiceClient(
    api_key="kb_sk_xxx",
    base_url="http://localhost:8020"
)

# 创建知识库
kb = client.knowledge_bases.create(
    name="技术文档库",
    description="存储技术文档"
)

# 上传文档
doc = client.documents.upload(
    kb_id=kb["id"],
    title="Python 教程",
    content="Python 是一种高级编程语言...",
    sensitivity_level="public"
)

# 检索
results = client.retrieve(
    query="Python 有什么应用？",
    kb_ids=[kb["id"]],
    top_k=5
)

# RAG 生成
answer = client.rag(
    query="Python 有什么应用？",
    kb_ids=[kb["id"]]
)
print(answer["answer"])

# OpenAI 兼容接口
response = client.openai.chat_completions(
    messages=[
        {"role": "user", "content": "Python 有什么应用？"}
    ],
    model="gpt-4",
    knowledge_base_ids=[kb["id"]]
)
```

### SDK 功能模块

#### 1. 知识库管理 (`client.knowledge_bases`)

```python
# 创建知识库
kb = client.knowledge_bases.create(
    name="技术文档",
    description="技术文档库",
    chunker="recursive",
    retriever="hybrid"
)

# 列出知识库
kbs = client.knowledge_bases.list()

# 获取详情
kb = client.knowledge_bases.get(kb_id="xxx")

# 删除知识库
client.knowledge_bases.delete(kb_id="xxx")
```

#### 2. 文档管理 (`client.documents`)

```python
# 上传文档
doc = client.documents.upload(
    kb_id="xxx",
    title="文档标题",
    content="文档内容...",
    sensitivity_level="public",  # public/internal/confidential/secret
    metadata={"author": "张三"}
)

# 列出文档
docs = client.documents.list(kb_id="xxx")

# 删除文档
client.documents.delete(doc_id="xxx")
```

#### 3. 检索 (`client.retrieve`)

```python
# 语义检索
results = client.retrieve(
    query="搜索内容",
    kb_ids=["kb1", "kb2"],
    top_k=10,
    score_threshold=0.5,
    metadata_filter={"author": "张三"}
)

for result in results["results"]:
    print(f"Score: {result['score']}")
    print(f"Text: {result['text']}")
```

#### 4. RAG 生成 (`client.rag`)

```python
# RAG 问答
answer = client.rag(
    query="Python 有什么应用？",
    kb_ids=["kb1"],
    top_k=5,
    temperature=0.7,
    max_tokens=500
)

print(f"回答: {answer['answer']}")
print(f"来源数量: {len(answer['sources'])}")
```

#### 5. API Key 管理 (`client.api_keys`)

```python
# 创建 API Key
key = client.api_keys.create(
    name="测试Key",
    role="read",  # admin/write/read
    scope_kb_ids=["kb1", "kb2"]
)
print(f"API Key: {key['api_key']}")  # 仅此一次返回

# 列出 API Keys
keys = client.api_keys.list()

# 删除 API Key
client.api_keys.delete(key_id="xxx")
```

#### 6. OpenAI 兼容接口 (`client.openai`)

```python
# Chat Completions (RAG 模式)
response = client.openai.chat_completions(
    messages=[
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "问题"}
    ],
    model="gpt-4",
    knowledge_base_ids=["kb1"],
    temperature=0.7
)

# Embeddings
emb_response = client.openai.embeddings(
    input="测试文本",
    model="text-embedding-v3"
)
```

### 错误处理

```python
from httpx import HTTPStatusError

try:
    kb = client.knowledge_bases.create(name="测试")
except HTTPStatusError as e:
    print(f"HTTP 错误: {e.response.status_code}")
    print(f"详情: {e.response.json()}")
except Exception as e:
    print(f"其他错误: {e}")
```

### 完整示例

详见 `test_openai_sdk.py`，包含 8 个测试场景：

1. OpenAI Embeddings API
2. SDK 知识库管理
3. SDK 文档管理
4. SDK 检索功能
5. SDK RAG 生成
6. SDK OpenAI Chat Completions
7. SDK OpenAI Embeddings
8. SDK API Key 管理

运行测试：
```bash
uv run python test_openai_sdk.py
```

---

## 实现文件

### API 路由
- `app/api/routes/openai_compat.py`: OpenAI 兼容接口实现
- `app/schemas/openai.py`: OpenAI 请求/响应 Schema

### SDK
- `sdk/client.py`: SDK 客户端实现
- `sdk/__init__.py`: SDK 导出
- `sdk/README.md`: SDK 详细文档

### 测试
- `test_openai_sdk.py`: 完整测试脚本
- `docs/OpenAI接口和SDK测试总结.md`: 测试总结文档

---

## 与智能体平台集成

### 1. 作为 LangChain 工具

```python
from langchain.tools import Tool
from kb_service_sdk import KBServiceClient

client = KBServiceClient(api_key="xxx", base_url="http://localhost:8020")

def kb_search(query: str) -> str:
    """搜索知识库"""
    results = client.retrieve(query=query, kb_ids=["kb1"], top_k=3)
    return "\n\n".join([r["text"] for r in results["results"]])

kb_tool = Tool(
    name="KnowledgeBaseSearch",
    func=kb_search,
    description="搜索技术文档知识库"
)
```

### 2. 作为 FastGPT 数据源

在 FastGPT 中配置自定义 HTTP 数据源：
- URL: `http://localhost:8020/v1/retrieve`
- Headers: `Authorization: Bearer kb_sk_xxx`
- Body: `{"query": "{{query}}", "kb_ids": ["kb1"], "top_k": 5}`

### 3. 作为 OpenAI 兼容端点

直接使用 OpenAI SDK 连接：

```python
from openai import OpenAI

client = OpenAI(
    api_key="kb_sk_xxx",
    base_url="http://localhost:8020/v1"
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Python 有什么应用？"}],
    extra_body={"knowledge_base_ids": ["kb1"]}
)
```

---

## 注意事项

1. **模型参数**: OpenAI 兼容接口中的 `model` 参数仅用于兼容性，实际使用的是服务端配置的模型
2. **RAG 模式**: 必须传入 `knowledge_base_ids` 参数才能启用 RAG，否则返回 501 错误
3. **API Key 权限**: 确保使用的 API Key 有足够的权限访问指定的知识库
4. **文档敏感度**: 检索时会根据 API Key 的 clearance 和文档的 sensitivity_level 进行 ACL 过滤
