# 知识库服务 Python SDK

官方 Python SDK，用于调用知识库服务 API。

## 安装

```bash
pip install httpx  # 依赖
```

## 快速开始

```python
from sdk import KBServiceClient

# 初始化客户端
client = KBServiceClient(
    api_key="kb_sk_xxx",
    base_url="http://localhost:8020"
)

# 创建知识库
kb = client.knowledge_bases.create("我的知识库")
print(f"知识库 ID: {kb['id']}")

# 上传文档
doc = client.documents.create(
    kb_id=kb["id"],
    title="Python 教程",
    content="Python 是一种高级编程语言..."
)
print(f"文档 ID: {doc['document_id']}, Chunks: {doc['chunk_count']}")

# 检索
results = client.retrieve(
    query="什么是 Python",
    knowledge_base_ids=[kb["id"]],
    top_k=5
)
for r in results["results"]:
    print(f"Score: {r['score']:.4f} | {r['text'][:50]}...")

# RAG 生成
answer = client.rag(
    query="什么是 Python",
    knowledge_base_ids=[kb["id"]]
)
print(f"回答: {answer['answer']}")

# 关闭连接
client.close()
```

## 使用上下文管理器（推荐）

```python
from sdk import KBServiceClient

with KBServiceClient(api_key="kb_sk_xxx") as client:
    kb = client.knowledge_bases.create("测试")
    # ... 其他操作
    # 自动关闭连接
```

## 功能模块

### 1. 知识库管理

```python
# 创建知识库
kb = client.knowledge_bases.create(
    name="技术文档",
    description="技术文档知识库",
    config={
        "ingestion": {
            "chunker": {"name": "recursive", "params": {"chunk_size": 500}}
        },
        "query": {
            "retriever": {"name": "hybrid"}
        }
    }
)

# 列出知识库
kbs = client.knowledge_bases.list(page=1, page_size=20)
print(f"总数: {kbs['total']}, 页数: {kbs['pages']}")

# 获取详情
kb_detail = client.knowledge_bases.get(kb_id="xxx")

# 更新知识库
client.knowledge_bases.update(
    kb_id="xxx",
    name="新名称",
    description="新描述"
)

# 删除知识库
client.knowledge_bases.delete(kb_id="xxx")
```

### 2. 文档管理

```python
# 创建文档
doc = client.documents.create(
    kb_id="xxx",
    title="文档标题",
    content="文档内容...",
    metadata={"author": "张三", "date": "2024-01-01"},
    source="manual",
    sensitivity_level="internal",  # public/internal/restricted
    acl={"roles": ["engineer"], "groups": ["dev-team"]}
)

# 从 URL 创建文档
doc = client.documents.create_from_url(
    kb_id="xxx",
    url="https://example.com/doc.md",
    title="远程文档"
)

# 上传文件
doc = client.documents.upload_file(
    kb_id="xxx",
    file_path="/path/to/file.pdf",
    title="PDF 文档"
)

# 批量创建文档
result = client.documents.batch_create(
    kb_id="xxx",
    documents=[
        {"title": "文档1", "content": "内容1"},
        {"title": "文档2", "content": "内容2"},
        {"title": "文档3", "content": "内容3"},
    ]
)

# 列出文档
docs = client.documents.list(kb_id="xxx", page=1, page_size=20)

# 获取文档详情
doc_detail = client.documents.get(document_id="xxx")

# 删除文档
client.documents.delete(document_id="xxx")
```

### 3. 检索

```python
# 基础检索
results = client.retrieve(
    query="查询问题",
    knowledge_base_ids=["kb1", "kb2"],
    top_k=10
)

# 高级检索
results = client.retrieve(
    query="查询问题",
    knowledge_base_ids=["kb1"],
    top_k=10,
    score_threshold=0.5,  # 相似度阈值
    metadata_filter={"author": "张三"},  # 元数据过滤
    retriever_override={"name": "hybrid"},  # 覆盖检索器
    rerank=True,  # 启用重排
    rerank_top_k=5,  # 重排后返回数量
    context_window=2  # 上下文窗口扩展
)

# 查看结果
for r in results["results"]:
    print(f"KB: {r['knowledge_base_id']}")
    print(f"Score: {r['score']:.4f}")
    print(f"Text: {r['text'][:100]}...")
    print(f"Metadata: {r['metadata']}")
    print("---")

# 查看模型信息
print(f"Embedding: {results['model']['embedding_provider']} / {results['model']['embedding_model']}")
print(f"Retriever: {results['model']['retriever']}")
```

### 4. RAG 生成

```python
# 基础 RAG
answer = client.rag(
    query="什么是 RAG",
    knowledge_base_ids=["kb1"]
)
print(f"回答: {answer['answer']}")
print(f"来源数量: {len(answer['sources'])}")

# 高级 RAG
answer = client.rag(
    query="什么是 RAG",
    knowledge_base_ids=["kb1"],
    top_k=5,
    score_threshold=0.3,
    system_prompt="你是一个专业的技术顾问，请基于提供的文档回答问题。",
    temperature=0.7,
    max_tokens=500,
    top_p=0.9
)

# 查看来源
for src in answer["sources"]:
    print(f"来源: {src['text'][:50]}... (Score: {src['score']:.4f})")
```

### 5. API Key 管理

```python
# 创建 API Key
key = client.api_keys.create(
    name="测试 Key",
    role="write",  # admin/write/read
    scope_kb_ids=["kb1", "kb2"],  # KB 白名单
    identity={
        "user_id": "user123",
        "roles": ["engineer"],
        "clearance": "restricted"
    },
    rate_limit_per_minute=60
)
print(f"API Key: {key['api_key']}")  # 仅此一次返回明文

# 列出 API Keys
keys = client.api_keys.list()
for k in keys["items"]:
    print(f"{k['name']} ({k['role']})")

# 删除 API Key
client.api_keys.delete(key_id="xxx")
```

### 6. OpenAI 兼容接口

```python
# Chat Completions
response = client.openai.chat_completions(
    messages=[
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "什么是 RAG？"}
    ],
    model="gpt-4",
    knowledge_base_ids=["kb1"],  # 启用 RAG
    temperature=0.7,
    max_tokens=500
)
print(response["choices"][0]["message"]["content"])

# Embeddings
response = client.openai.embeddings(
    input="Hello, world!",
    model="text-embedding-3-small"
)
print(f"向量维度: {len(response['data'][0]['embedding'])}")

# 批量 Embeddings
response = client.openai.embeddings(
    input=["文本1", "文本2", "文本3"],
    model="text-embedding-3-small"
)
for i, emb in enumerate(response["data"]):
    print(f"文本{i+1} 向量维度: {len(emb['embedding'])}")
```

## 错误处理

```python
import httpx

try:
    kb = client.knowledge_bases.create("测试")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 403:
        print("权限不足")
    elif e.response.status_code == 404:
        print("资源不存在")
    else:
        print(f"HTTP 错误: {e.response.status_code}")
        print(f"详情: {e.response.json()}")
except httpx.RequestError as e:
    print(f"请求失败: {e}")
```

## 完整示例

```python
from sdk import KBServiceClient

def main():
    # 初始化客户端
    with KBServiceClient(api_key="kb_sk_xxx") as client:
        # 1. 创建知识库
        kb = client.knowledge_bases.create(
            name="Python 教程",
            config={
                "ingestion": {
                    "chunker": {"name": "recursive", "params": {"chunk_size": 500}}
                },
                "query": {
                    "retriever": {"name": "hybrid"}
                }
            }
        )
        print(f"✓ 创建知识库: {kb['id']}")
        
        # 2. 上传文档
        docs = [
            {"title": "Python 基础", "content": "Python 是一种解释型、面向对象的编程语言..."},
            {"title": "Python 高级", "content": "装饰器、生成器、上下文管理器..."},
            {"title": "Python 应用", "content": "Web 开发、数据分析、机器学习..."},
        ]
        
        result = client.documents.batch_create(kb_id=kb["id"], documents=docs)
        print(f"✓ 批量上传: {result['success_count']} 个文档")
        
        # 3. 检索测试
        results = client.retrieve(
            query="Python 有什么应用",
            knowledge_base_ids=[kb["id"]],
            top_k=3
        )
        print(f"\n✓ 检索结果 ({len(results['results'])} 条):")
        for r in results["results"]:
            print(f"  - Score: {r['score']:.4f} | {r['text'][:50]}...")
        
        # 4. RAG 生成
        answer = client.rag(
            query="Python 有什么应用",
            knowledge_base_ids=[kb["id"]],
            temperature=0.7
        )
        print(f"\n✓ RAG 回答:\n{answer['answer']}")
        
        # 5. 清理
        client.knowledge_bases.delete(kb_id=kb["id"])
        print(f"\n✓ 清理完成")

if __name__ == "__main__":
    main()
```

## 环境变量

```bash
# 设置默认配置
export KB_API_KEY="kb_sk_xxx"
export KB_BASE_URL="http://localhost:8020"
```

```python
import os
from sdk import KBServiceClient

client = KBServiceClient(
    api_key=os.getenv("KB_API_KEY"),
    base_url=os.getenv("KB_BASE_URL", "http://localhost:8020")
)
```

## 高级配置

### 自定义超时

```python
client = KBServiceClient(
    api_key="kb_sk_xxx",
    timeout=60.0  # 60 秒超时
)
```

### 使用 OpenAI SDK

本服务提供 OpenAI 兼容接口，可直接使用 OpenAI SDK：

```python
from openai import OpenAI

client = OpenAI(
    api_key="kb_sk_xxx",
    base_url="http://localhost:8020/v1"
)

# Chat Completions (RAG 模式)
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "什么是 RAG？"}],
    extra_body={"knowledge_base_ids": ["kb1"]}
)
print(response.choices[0].message.content)

# Embeddings
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Hello, world!"
)
print(response.data[0].embedding)
```

## 许可证

MIT License
