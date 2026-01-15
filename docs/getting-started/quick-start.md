# 快速开始

本指南将通过一个完整的示例，帮助您快速上手 Self-RAG Pipeline 服务。

## 前提条件

- 已完成[安装](installation.md)并启动服务
- 已获取 API Key（通过管理员 API 创建租户时返回）

## 基本概念

在开始之前，了解几个核心概念：

- **租户（Tenant）**：多租户系统中的独立用户或组织
- **知识库（Knowledge Base）**：存储相关文档的容器
- **文档（Document）**：上传到知识库的文本内容
- **检索（Retrieve）**：从知识库中查找相关文档片段
- **RAG（Retrieval-Augmented Generation）**：检索增强生成，结合检索和 LLM 生成答案

## 完整示例：创建食品安全法规知识库

### 步骤 1：设置环境变量

```bash
# 设置 API Key（从租户创建时获得）
export API_KEY="kb_sk_Ccuv2Qqz84WesEHscCMUljqVGWx736nV85yu6z8kGsg"
export API_BASE="http://localhost:8020"
```

### 步骤 2：创建知识库

```bash
# 创建知识库
curl -X POST "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "食品安全法规",
    "description": "中国食品安全相关法律法规知识库",
    "config": {
      "chunker": "sliding_window",
      "chunker_params": {"window": 1024, "overlap": 100},
      "retriever": "hybrid",
      "retriever_params": {"dense_weight": 0.7, "sparse_weight": 0.3}
    }
  }'
```

**响应示例**：
```json
{
  "id": "a7899231-4489-423c-b15d-f67c3c9a2e24",
  "name": "食品安全法规",
  "description": "中国食品安全相关法律法规知识库",
  "status": "active",
  "created_at": "2024-12-08T10:00:00Z"
}
```

保存返回的知识库 ID：
```bash
export KB_ID="a7899231-4489-423c-b15d-f67c3c9a2e24"
```

### 步骤 3：上传文档

#### 方式一：JSON 内容上传（适合小文件）

```bash
# 上传第一个文档
curl -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "中华人民共和国食品安全法",
    "content": "第一章 总则\n第一条 为了保证食品安全，保障公众身体健康和生命安全，制定本法。\n第二条 在中华人民共和国境内从事下列活动，应当遵守本法：\n（一）食品生产和加工（以下称食品生产），食品销售和餐饮服务（以下称食品经营）；\n（二）食品添加剂的生产经营；\n（三）用于食品的包装材料、容器、洗涤剂、消毒剂和用于食品生产经营的工具、设备（以下称食品相关产品）的生产经营；\n（四）食品生产经营者使用食品添加剂、食品相关产品；\n（五）对食品、食品添加剂、食品相关产品的安全管理。",
    "metadata": {
      "source": "法律法规",
      "category": "食品安全法",
      "year": "2015"
    }
  }'
```

#### 方式二：文件上传（适合大文件）

```bash
# 准备文档文件
echo "食品生产许可证管理办法详细内容..." > food_license.md

# 上传文件
curl -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@food_license.md" \
  -F "metadata={\"source\": \"管理办法\", \"category\": \"许可证管理\"}"
```

### 步骤 4：检索测试

#### 基础检索

```bash
# 执行语义检索
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品生产许可证的有效期是多久？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5
  }'
```

**响应示例**：
```json
{
  "results": [
    {
      "chunk_id": "chunk_001",
      "text": "食品生产许可证有效期为5年。食品生产者应当在食品生产许可有效期届满30个工作日前，向原发证的食品药品监督管理部门提出延续申请。",
      "score": 0.92,
      "metadata": {
        "kb_id": "a7899231-4489-423c-b15d-f67c3c9a2e24",
        "doc_id": "doc_001",
        "title": "食品生产许可管理办法",
        "source": "管理办法"
      },
      "knowledge_base_id": "a7899231-4489-423c-b15d-f67c3c9a2e24"
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "retriever": "hybrid"
  }
}
```

#### 高级检索：使用 HyDE

```bash
# 使用 HyDE 检索器处理复杂查询
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品安全日管控、周排查、月调度的具体要求是什么？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "retriever_override": {"name": "hyde"},
    "top_k": 5
  }'
```

### 步骤 5：RAG 生成

#### 使用原生 RAG 接口

```bash
# RAG 问答
curl -X POST "$API_BASE/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "菊粉是什么？它被批准为新资源食品了吗？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5,
    "temperature": 0.7
  }'
```

**响应示例**：
```json
{
  "answer": "菊粉是一种来源于菊苣根的果糖聚合体，属于水溶性膳食纤维。根据相关法规文件，菊粉已被批准为新资源食品。卫生部在相关公告中明确批准了菊粉作为新资源食品，可以用于食品生产和加工。",
  "sources": [
    {
      "chunk_id": "chunk_005",
      "text": "卫生部关于批准菊粉、多聚果糖为新资源食品的公告...",
      "score": 0.89,
      "knowledge_base_id": "a7899231-4489-423c-b15d-f67c3c9a2e24",
      "document_id": "doc_005"
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "retriever": "dense"
  },
  "retrieval_count": 5
}
```

#### 使用 OpenAI 兼容接口

```bash
# OpenAI Chat Completions API（RAG 模式）
curl -X POST "$API_BASE/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "system", "content": "你是一个食品安全法规专家，请基于提供的法规文档回答问题。"},
      {"role": "user", "content": "食品生产企业需要建立哪些管理制度？"}
    ],
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

### 步骤 6：管理知识库

#### 查看知识库列表

```bash
curl -X GET "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"
```

#### 查看文档列表

```bash
curl -X GET "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY"
```

#### 删除文档

```bash
# 获取文档 ID 后删除
curl -X DELETE "$API_BASE/v1/documents/{document_id}" \
  -H "Authorization: Bearer $API_KEY"
```

## 使用 Python SDK

### 安装 SDK

```bash
pip install kb-service-sdk
```

### Python 示例

```python
from kb_service_sdk import KBServiceClient

# 初始化客户端
client = KBServiceClient(
    api_key="kb_sk_Ccuv2Qqz84WesEHscCMUljqVGWx736nV85yu6z8kGsg",
    base_url="http://localhost:8020"
)

# 创建知识库
kb = client.knowledge_bases.create(
    name="技术文档库",
    description="存储技术文档和API参考"
)
print(f"创建知识库: {kb['id']}")

# 上传文档
doc = client.documents.upload(
    kb_id=kb["id"],
    title="Python 编程指南",
    content="""
    Python 是一种高级编程语言，具有以下特点：
    1. 语法简洁易读
    2. 面向对象编程
    3. 丰富的标准库
    4. 跨平台支持
    5. 活跃的社区
    """,
    metadata={"category": "编程语言", "level": "入门"}
)
print(f"上传文档: {doc['id']}")

# 检索
results = client.retrieve(
    query="Python 有什么特点？",
    kb_ids=[kb["id"]],
    top_k=3
)
print(f"检索到 {len(results['results'])} 个结果")

# RAG 生成
answer = client.rag(
    query="Python 适合什么场景使用？",
    kb_ids=[kb["id"]],
    temperature=0.7
)
print(f"RAG 回答: {answer['answer']}")

# OpenAI 兼容接口
response = client.openai.chat_completions(
    messages=[
        {"role": "user", "content": "Python 和 Java 有什么区别？"}
    ],
    model="gpt-4",
    knowledge_base_ids=[kb["id"]]
)
print(f"Chat 回答: {response['choices'][0]['message']['content']}")
```

## 高级功能示例

### 1. 使用不同的检索器

```bash
# 纯向量检索
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品添加剂使用标准",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "retriever_override": {"name": "dense"}
  }'

# BM25 关键词检索
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品添加剂使用标准",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "retriever_override": {"name": "bm25"}
  }'

# 融合检索 + 重排
curl -X POST "$API_BASE/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品添加剂使用标准",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "retriever_override": {
      "name": "fusion",
      "params": {"rerank": true}
    }
  }'
```

### 2. 文档权限控制

```bash
# 上传受限文档
curl -X POST "$API_BASE/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "内部管理制度",
    "content": "企业内部管理制度内容...",
    "sensitivity_level": "restricted",
    "acl_allow_roles": ["manager", "admin"],
    "acl_allow_groups": ["management_team"]
  }'
```

### 3. 批量操作

```python
# 批量上传文档
documents = [
    {"title": "文档1", "content": "内容1"},
    {"title": "文档2", "content": "内容2"},
    {"title": "文档3", "content": "内容3"}
]

for doc in documents:
    client.documents.upload(
        kb_id=kb_id,
        title=doc["title"],
        content=doc["content"]
    )
```

## 性能优化建议

### 1. 切分策略选择

- **简单文档**：使用 `simple` 切分器
- **长篇文章**：使用 `parent_child` 切分器
- **技术文档**：使用 `markdown` 切分器
- **代码文档**：使用 `code` 切分器

### 2. 检索器选择

- **语义相似**：使用 `dense` 检索器
- **精确匹配**：使用 `bm25` 检索器
- **通用场景**：使用 `hybrid` 检索器（推荐）
- **复杂查询**：使用 `hyde` 检索器
- **高质量召回**：使用 `fusion` + rerank

### 3. 参数调优

```json
{
  "config": {
    "chunker": "sliding_window",
    "chunker_params": {
      "window": 1024,    // 根据文档类型调整
      "overlap": 100     // 保持上下文连贯性
    },
    "retriever": "hybrid",
    "retriever_params": {
      "dense_weight": 0.7,   // 语义权重
      "sparse_weight": 0.3   // 关键词权重
    }
  }
}
```

## 故障排查

### 常见问题

1. **检索结果为空**
   - 检查知识库是否有文档
   - 确认文档已成功索引
   - 尝试降低 `score_threshold`

2. **RAG 回答不准确**
   - 增加 `top_k` 获取更多上下文
   - 尝试不同的检索器
   - 调整 LLM 温度参数

3. **权限被拒绝**
   - 检查 API Key 权限
   - 确认文档敏感度设置
   - 验证 ACL 配置

### 调试技巧

```bash
# 查看系统状态
curl "$API_BASE/health"
curl "$API_BASE/ready"
curl "$API_BASE/metrics"

# 查看日志
docker compose logs -f api

# 检查知识库配置
curl -X GET "$API_BASE/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $API_KEY"
```

## 下一步

完成快速开始后，您可以：

1. 学习[第一个 API 调用](first-api-call.md)的详细说明
2. 查看[开发文档](../development/)了解高级功能
3. 阅读[架构文档](../architecture/)理解系统设计
4. 参考[运维指南](../operations/)进行生产部署

## 相关资源

- [API 参考文档](../architecture/api-specification.md)
- [Python SDK 文档](../../sdk/README.md)
- [算法框架说明](../architecture/pipeline-architecture.md)
- [部署指南](../operations/deployment.md)