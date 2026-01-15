# Self-RAG Pipeline 实践总结

> 实践日期：2024-12-08

## 一、环境信息

| 配置项 | 值 |
|--------|-----|
| API 服务 | http://localhost:8020 |
| Embedding | Ollama / bge-m3 (1024维) |
| LLM | Ollama / qwen3:14b |
| 向量库 | Qdrant |
| 数据库 | PostgreSQL |

## 二、知识库创建

### 2.1 创建租户和知识库

```bash
# 创建租户（获取 admin API Key）
curl -s -X POST "http://localhost:8020/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "rag-demo"}'

# 创建知识库
curl -s -X POST "http://localhost:8020/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "食品安全法规", "description": "中国食品安全相关法律法规"}'
```

### 2.2 本次知识库统计

| 项目 | 数值 |
|------|------|
| 知识库名称 | 食品安全法规 |
| 文档数量 | 20 |
| Chunk 总数 | ~1900 |
| 文档类型 | Markdown 法规文档 |
| KB_ID | `a7899231-4489-423c-b15d-f67c3c9a2e24` |

### 2.3 文档列表

- 中华人民共和国食品安全法 (427 chunks)
- 中华人民共和国广告法 (193 chunks)
- 食品生产许可审查通则 (195 chunks)
- 中华人民共和国进出口食品安全管理办法 (160 chunks)
- 中华人民共和国食品安全法实施条例 (147 chunks)
- 食品生产许可管理办法 (122 chunks)
- 食品生产经营监督检查管理办法 (104 chunks)
- 等共 20 个法规文档

## 三、文档上传方式

### 3.1 JSON 内容上传（小文件）

```bash
CONTENT=$(cat document.md | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
curl -s -X POST "http://localhost:8020/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"文档标题\", \"content\": $CONTENT}"
```

### 3.2 文件上传（大文件）

```bash
curl -s -X POST "http://localhost:8020/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@/path/to/large-document.md"
```

## 四、检索测试

### 4.1 语义检索 `/v1/retrieve`

```bash
curl -s -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品生产许可证的有效期是多久",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5
  }'
```

**返回结果**：
- 检索器：dense
- 返回 top_k 个最相关的文档片段
- 包含 score、text、metadata 等字段

### 4.2 可选检索器

| 检索器 | 说明 | 使用场景 |
|--------|------|----------|
| `dense` | 稠密向量检索（默认） | 通用语义匹配 |
| `bm25` | BM25 关键词检索 | 精确术语匹配 |
| `hybrid` | 混合检索 | 综合匹配 |
| `hyde` | HyDE 假设文档检索 | 复杂查询 |
| `fusion` | RRF 融合 + 可选 Rerank | 高精度场景 |

## 五、RAG 生成测试

### 5.1 原生 RAG 接口 `/v1/rag`

```bash
curl -s -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "菊粉是什么？它被批准为新资源食品了吗？",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5
  }'
```

**返回结果**：
```json
{
  "answer": "菊粉是一种来源于菊苣根的果糖聚合体...",
  "retrieval_count": 5,
  "model": {
    "retriever": "dense",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b"
  }
}
```

### 5.2 OpenAI 兼容接口 `/v1/chat/completions`

```bash
curl -s -X POST "http://localhost:8020/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "菊粉是什么？"}],
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 5
  }'
```

**返回结果**：OpenAI 标准格式，包含 choices、usage 等字段

## 六、高级检索示例

### 6.1 使用 HyDE 检索器

```bash
curl -s -X POST "http://localhost:8020/v1/rag" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品安全日管控、周排查、月调度具体要求是什么",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "retriever_override": {"name": "hyde"}
  }'
```

### 6.2 使用 Fusion + Rerank

```bash
curl -s -X POST "http://localhost:8020/v1/retrieve" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "新资源食品批准流程",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "retriever_override": {"name": "fusion", "params": {"rerank": true}}
  }'
```

## 七、测试结论

### 7.1 RAG 效果观察

1. **语义理解**：LLM 能正确理解问题并从检索结果中提取关键信息
2. **知识边界**：当文档中没有相关信息时，LLM 会明确说明"未提及"
3. **推理能力**：LLM 能根据文档内容进行合理推断和补充说明
4. **来源追溯**：支持返回检索来源，便于验证答案可靠性

### 7.2 优化建议

1. **切分策略**：法规文档适合使用 `markdown` 切分器，按章节分块
2. **检索器选择**：
   - 专业术语查询：使用 `hybrid` 或 `bm25`
   - 复杂语义查询：使用 `hyde`
   - 高精度场景：使用 `fusion` + rerank
3. **上下文窗口**：可启用 `context_window` 后处理，获取更完整上下文

## 八、环境变量参考

```bash
# 测试环境变量
source /tmp/rag_demo.env

# 包含：
# API_KEY=kb_sk_Ccuv2Qqz84WesEHscCMUljqVGWx736nV85yu6z8kGsg
# KB_ID=a7899231-4489-423c-b15d-f67c3c9a2e24
```

## 九、相关文档

- [API 设计文档](./API设计.md)
- [测试记录](./测试记录.md)
- [优化方案](./优化.md)
- [部署指南](./部署.md)
