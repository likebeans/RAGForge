# RAGForge ACL 权限测试指南

> 测试时间：2026-01-26  
> 测试环境：http://192.168.168.105:8020  
> Admin Key：`kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ`

## 测试目标

验证 RAGForge 三层权限模型中的 **文档级 ACL** 功能：

1. 创建不同敏感度级别的文档（public/restricted）
2. 创建带不同 identity 的 API Key
3. 验证检索时 ACL 过滤是否生效

---

## 第一步：创建测试知识库

```bash
BASE_URL="http://192.168.168.105:8020"
ADMIN_KEY="kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ"

# 创建测试知识库
curl -X POST "$BASE_URL/v1/knowledge-bases" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACL权限测试库",
    "description": "用于测试文档级权限控制"
  }'
```

**返回示例**：
```json
{
  "id": "bd3da9d3-28cd-41ce-b14b-469facb7ac87",
  "name": "ACL权限测试库"
}
```

---

## 第二步：创建带 ACL 的测试文档

### 2.1 公开文档 (sensitivity_level: public)

```bash
KB_ID="你的知识库ID"

curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "权限测试-公开文档",
    "content": "这是一份公开文档，包含公司简介和产品介绍。任何人都可以查看这份公开资料。",
    "sensitivity_level": "public"
  }'
```

### 2.2 财务机密文档 (restricted, 只允许 finance 角色)

```bash
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "权限测试-财务机密",
    "content": "这是财务部门的机密预算报告，包含年度财务预算和薪资方案。只有财务角色可以查看。",
    "sensitivity_level": "restricted",
    "acl_roles": ["finance"]
  }'
```

> ⚠️ **注意**：字段名是 `acl_roles`，不是 `acl_allow_roles`

### 2.3 技术机密文档 (restricted, 只允许 tech/engineering 角色)

```bash
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "权限测试-技术机密",
    "content": "这是技术部门的核心算法文档，包含系统架构和加密算法。只有技术角色可以查看。",
    "sensitivity_level": "restricted",
    "acl_roles": ["tech", "engineering"]
  }'
```

---

## 第三步：创建带 Identity 的 API Key

### 3.1 财务人员 Key (identity: finance 角色, clearance: restricted)

```bash
curl -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "财务测试Key",
    "role": "read",
    "identity": {
      "user_id": "finance_user",
      "roles": ["finance"],
      "groups": ["dept_finance"],
      "clearance": "restricted"
    }
  }'
```

**返回示例**：
```json
{
  "id": "57df7657-9850-4dc7-aeb6-551cafe536af",
  "name": "财务测试Key",
  "api_key": "kb_sk_ug2cjjCjD6e4dndYEQ30LQuazoe_L5dN-sNV_J52Uo0",
  "identity": {
    "user_id": "finance_user",
    "roles": ["finance"],
    "groups": ["dept_finance"],
    "clearance": "restricted"
  }
}
```

### 3.2 技术人员 Key (identity: tech 角色, clearance: restricted)

```bash
curl -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术测试Key",
    "role": "read",
    "identity": {
      "user_id": "tech_user",
      "roles": ["tech", "engineering"],
      "groups": ["dept_tech"],
      "clearance": "restricted"
    }
  }'
```

### 3.3 普通用户 Key (clearance: public, 只能看公开文档)

```bash
curl -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "普通用户Key",
    "role": "read",
    "identity": {
      "user_id": "normal_user",
      "roles": ["viewer"],
      "groups": ["dept_general"],
      "clearance": "public"
    }
  }'
```

---

## 第四步：检索测试（验证 ACL 过滤）

### 4.1 Admin Key - 应该看到所有文档

```bash
curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "财务预算 技术算法 公司简介",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 10
  }'
```

**期望结果**：返回全部3个文档（公开 + 财务 + 技术）

### 4.2 财务 Key - 应该只看到公开 + 财务文档

```bash
FINANCE_KEY="kb_sk_ug2cjjCjD6e4dndYEQ30LQuazoe_L5dN-sNV_J52Uo0"

curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $FINANCE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "财务预算 技术算法 公司简介",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 10
  }'
```

**期望结果**：
- ✅ 返回：权限测试-公开文档
- ✅ 返回：权限测试-财务机密
- ❌ 不返回：权限测试-技术机密

### 4.3 技术 Key - 应该只看到公开 + 技术文档

```bash
TECH_KEY="kb_sk_QD0BZ-4NJjE-w0nLV-jEjs__tl46JknOy6n8uBkyA9s"

curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $TECH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "财务预算 技术算法 公司简介",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 10
  }'
```

**期望结果**：
- ✅ 返回：权限测试-公开文档
- ❌ 不返回：权限测试-财务机密
- ✅ 返回：权限测试-技术机密

### 4.4 普通 Key (clearance=public) - 应该只看到公开文档

```bash
NORMAL_KEY="kb_sk_blqSkxfi6-6-NmUwhRg8ypm7dkDCgSNXbt2pssOF46Y"

curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $NORMAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "财务预算 技术算法 公司简介",
    "knowledge_base_ids": ["'"$KB_ID"'"],
    "top_k": 10
  }'
```

**期望结果**：
- ✅ 返回：权限测试-公开文档
- ❌ 不返回：权限测试-财务机密（因为 clearance=public 无法访问 restricted）
- ❌ 不返回：权限测试-技术机密

---

## 当前发现的问题

### 问题1：向量索引失败

**现象**：文档创建成功（status=completed），但检索返回空结果

**查看文档处理日志**：
```bash
curl "$BASE_URL/v1/documents/$DOC_ID" \
  -H "Authorization: Bearer $ADMIN_KEY"
```

**日志中的错误**：
```
[ERROR] 向量库写入失败: SILICONFLOW_API_KEY 未配置，无法生成真实 Embedding
```

**根本原因**：RAGForge 服务器未配置 `SILICONFLOW_API_KEY` 环境变量，导致无法生成文档 Embedding。

**修复方法**：在 RAGForge 服务器配置环境变量：
```bash
export SILICONFLOW_API_KEY="your_siliconflow_api_key"
```

### 问题2：检查 ACL 元数据是否正确存储

确认文档的 `sensitivity_level` 和 `acl_allow_roles` 是否正确存储到向量库中：

```bash
# 检索结果中应该包含 metadata.sensitivity_level
curl -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "权限测试", "knowledge_base_ids": ["'"$KB_ID"'"], "top_k": 5}'
```

检查返回的 `results[].metadata` 中是否有：
- `sensitivity_level`: "public" 或 "restricted"
- 对于 restricted 文档，向量库中应存储 ACL 字段用于过滤

---

## ACL 过滤逻辑（参考实现）

根据 `PERMISSION_MANAGEMENT.md`，ACL 过滤应该采用两阶段：

### 阶段1：向量库层面过滤（Qdrant Filter）

```python
{
  "should": [
    {"key": "sensitivity_level", "match": {"value": "public"}},
    {"key": "acl_users", "match": {"any": [user_id]}},
    {"key": "acl_roles", "match": {"any": user_roles}},
    {"key": "acl_groups", "match": {"any": user_groups}}
  ]
}
```

### 阶段2：应用层二次过滤

```python
def filter_results_by_acl(results, user_context):
    if user_context.is_admin:
        return results
    
    if user_context.clearance == "public":
        return [r for r in results if r.sensitivity_level == "public"]
    
    return [r for r in results if check_acl_match(r, user_context)]
```

---

## 测试检查清单

| 测试项 | 预期结果 | 实际结果 |
|--------|---------|---------|
| API Key 创建带 identity | 成功创建 | ✅ |
| 文档创建带 ACL | API 接受参数（用 `acl_roles`） | ✅ |
| 文档 Embedding 索引 | 写入向量库 | ✅ 已修复（需配置 KB embedding） |
| Admin 检索全部文档 | 返回全部 | ✅ 返回 5 条 |
| Finance Key 检索 | 只返回 public + finance | ✅ 返回 2 条 |
| Tech Key 检索 | 只返回 public + tech | ✅ 返回 2 条 |
| Public clearance 检索 | 只返回 public | ✅ 返回 1 条 |

---

## 完整测试脚本

```bash
#!/bin/bash

BASE_URL="http://192.168.168.105:8020"
ADMIN_KEY="kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ"

# 1. 创建知识库（必须配置 embedding）
echo "=== 创建测试知识库 ==="
KB_RESULT=$(curl -s -X POST "$BASE_URL/v1/knowledge-bases" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACL测试",
    "description": "权限测试",
    "config": {
      "embedding": {
        "provider": "siliconflow",
        "model": "Qwen/Qwen3-Embedding-4B"
      }
    }
  }')
KB_ID=$(echo $KB_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "知识库ID: $KB_ID"

# 2. 创建文档
echo "=== 创建公开文档 ==="
curl -s -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"公开文档","content":"公开内容","sensitivity_level":"public"}'

echo "=== 创建财务机密 ==="
curl -s -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"财务机密","content":"财务预算","sensitivity_level":"restricted","acl_roles":["finance"]}'

echo "=== 创建技术机密 ==="
curl -s -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"技术机密","content":"核心算法","sensitivity_level":"restricted","acl_roles":["tech"]}'

# 3. 等待索引
echo "=== 等待5秒 ==="
sleep 5

# 4. 创建测试 Key
echo "=== 创建财务Key ==="
FINANCE_KEY=$(curl -s -X POST "$BASE_URL/v1/api-keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"财务Key","role":"read","identity":{"user_id":"fin","roles":["finance"],"clearance":"restricted"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_key',''))")
echo "财务Key: $FINANCE_KEY"

# 5. 测试检索
echo "=== Admin检索 ==="
curl -s -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"文档\",\"knowledge_base_ids\":[\"$KB_ID\"],\"top_k\":5}" | python3 -c "
import sys,json
for r in json.load(sys.stdin).get('results',[]):
    print(f'  {r[\"metadata\"].get(\"title\")} [{r[\"metadata\"].get(\"sensitivity_level\")}]')
"

echo "=== 财务Key检索 ==="
curl -s -X POST "$BASE_URL/v1/retrieve" \
  -H "Authorization: Bearer $FINANCE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"文档\",\"knowledge_base_ids\":[\"$KB_ID\"],\"top_k\":5}" | python3 -c "
import sys,json
for r in json.load(sys.stdin).get('results',[]):
    print(f'  {r[\"metadata\"].get(\"title\")} [{r[\"metadata\"].get(\"sensitivity_level\")}]')
"
```

---

## 问题修复记录（2026-01-26）

### 已修复问题

1. **SILICONFLOW_API_KEY 未配置** → 已修复
   - 原因：`documents.py` 入库接口未从租户配置获取 embedding 配置
   - 修复：添加 `model_config_resolver` 获取租户 API Key

2. **Qdrant 连接失败** → 已修复
   - 原因：多后端写入默认尝试 Qdrant（即使使用 pgvector）
   - 修复：`_maybe_upsert_llamaindex` 未配置时跳过

3. **向量维度冲突** → 已修复错误提示
   - 原因：KB 无 embedding 配置时回退到租户默认模型，与已有数据维度不匹配
   - 修复：`vector_store_pg.py` 检测冲突时给出清晰错误

4. **ACL 角色未保存** → 文档字段名错误
   - 原因：测试指南使用 `acl_allow_roles`，但 API schema 定义为 `acl_roles`
   - 修复：使用正确字段名 `acl_roles`、`acl_users`、`acl_groups`

### 重要：创建 KB 时必须配置 embedding

```bash
curl -X POST "$BASE_URL/v1/knowledge-bases" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACL权限测试库",
    "description": "用于测试文档级权限控制",
    "config": {
      "embedding": {
        "provider": "siliconflow",
        "model": "Qwen/Qwen3-Embedding-4B"
      }
    }
  }'
```

### 测试通过的 KB

- **名称**: ACL测试v6-带embedding配置
- **ID**: `6ce20955-07cf-4f3e-bb9c-4b86858421b8`
- **Embedding**: `siliconflow/Qwen/Qwen3-Embedding-4B` (2560维)

---

## 后续待办

1. ~~配置 SILICONFLOW_API_KEY~~ ✅ 已修复
2. **测试 ACL 过滤** - 验证不同 identity 的检索结果
3. **添加 ACL 相关单元测试** - 在 RAGForge 项目中添加自动化测试
