# RAGForge 权限管理文档

> **版本**: v1.0  
> **更新时间**: 2026-01-26  
> **适用版本**: RAGForge 0.2.0+

## 目录

- [概述](#概述)
- [权限管理架构](#权限管理架构)
- [第一层：租户隔离](#第一层租户隔离)
- [第二层：API Key 角色权限](#第二层api-key-角色权限)
- [第三层：文档级 ACL](#第三层文档级-acl)
- [认证与授权流程](#认证与授权流程)
- [限流机制](#限流机制)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 概述

RAGForge 实现了一套**三层权限模型**，结合了**多租户隔离**、**角色权限控制（RBAC）**和**文档级访问控制列表（ACL）**，形成了完整的企业级权限管理体系。

### 核心特性

- ✅ **多租户隔离**：完整的租户数据隔离和配额管理
- ✅ **角色权限控制**：admin/write/read 三级角色
- ✅ **KB 访问白名单**：限制 API Key 访问特定知识库
- ✅ **文档级 ACL**：基于用户/角色/组的细粒度权限
- ✅ **Security Trimming**：检索时自动过滤无权限文档
- ✅ **限流保护**：支持内存和 Redis 两种限流器

---

## 权限管理架构

```
┌─────────────────────────────────────────────────────────────┐
│                    请求认证与授权流程                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  第一层：租户隔离 (Tenant Isolation)                          │
│  - 所有数据表包含 tenant_id 字段                              │
│  - 租户状态检查 (active/disabled/pending)                    │
│  - 配额管理 (KB数量/文档数量/存储空间)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  第二层：API Key 角色权限 (RBAC)                              │
│  - admin: 全部权限 + 管理 API Key                            │
│  - write: 创建/删除 KB、上传文档、检索                        │
│  - read: 仅检索和列表查询                                     │
│  - scope_kb_ids: KB 访问白名单（可选）                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  第三层：文档级 ACL (Security Trimming)                       │
│  - 敏感度级别: public / restricted                           │
│  - ACL 白名单: users / roles / groups                        │
│  - 检索时自动过滤无权限文档                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 第一层：租户隔离

### 租户模型

每个租户拥有独立的数据空间和配额限制：

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | String | 租户状态：active/disabled/pending |
| `quota_kb_count` | Integer | 知识库数量限制，-1=无限 |
| `quota_doc_count` | Integer | 文档数量限制，-1=无限 |
| `quota_storage_mb` | Integer | 存储空间限制(MB)，-1=无限 |
| `disabled_at` | DateTime | 禁用时间 |
| `disabled_reason` | Text | 禁用原因 |

### 租户状态

- **active**: 正常使用
- **disabled**: 已禁用，所有 API Key 失效
- **pending**: 待激活（新创建）

### 数据隔离

所有业务表都包含 `tenant_id` 字段，查询时强制过滤：

```python
# 查询知识库时自动过滤租户
result = await db.execute(
    select(KnowledgeBase)
    .where(KnowledgeBase.tenant_id == tenant.id)
)
```

### 配额管理

创建租户时设置配额：

```bash
curl -X POST -H "X-Admin-Token: your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "企业A",
    "quota_kb_count": 10,
    "quota_doc_count": 1000,
    "quota_storage_mb": 5120
  }' \
  "http://localhost:8020/admin/tenants"
```

---

## 第二层：API Key 角色权限

### API Key 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | String | 角色：admin/write/read |
| `scope_kb_ids` | JSON | KB 访问白名单，null=全部 |
| `is_initial` | Boolean | 是否为初始管理员 Key |
| `identity` | JSON | 身份信息（用于文档 ACL） |
| `revoked` | Boolean | 是否已撤销 |
| `expires_at` | DateTime | 过期时间 |
| `rate_limit_per_minute` | Integer | 独立限流配置 |

### 角色权限定义

| 角色 | 权限范围 | 典型用途 |
|------|---------|---------|
| **admin** | 全部权限 + 管理 API Key | 租户管理员 |
| **write** | 创建/删除 KB、上传文档、检索 | 内容管理员 |
| **read** | 仅检索和列表查询 | 只读用户/应用 |

### 角色权限示例

#### 创建只读 API Key

```bash
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "客服系统只读Key",
    "role": "read",
    "description": "用于客服系统的只读访问"
  }' \
  "http://localhost:8020/v1/api-keys"
```

#### 创建带 KB 白名单的 API Key

```bash
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档访问Key",
    "role": "read",
    "scope_kb_ids": ["kb_product_manual", "kb_faq"],
    "description": "只能访问产品手册和FAQ"
  }' \
  "http://localhost:8020/v1/api-keys"
```

### KB 访问白名单 (scope_kb_ids)

限制 API Key 只能访问特定知识库：

**工作原理**：
1. API Key 设置 `scope_kb_ids` 字段（JSON 数组）
2. 检索/RAG 请求时检查请求的 KB 是否在白名单中
3. 如果不在白名单中，返回 403 错误

**使用场景**：
- 多应用共享租户时的权限细分
- 限制外部系统访问范围
- 实现知识库级别的权限隔离

**错误示例**：
```json
{
  "code": "KB_ACCESS_DENIED",
  "detail": "Access denied to KBs: ['kb_internal_docs']"
}
```

### API Key 安全设计

- ✅ **明文 Key 仅显示一次**：创建后无法恢复
- ✅ **SHA256 哈希存储**：数据库只存储哈希值
- ✅ **前缀快速定位**：避免全表扫描
- ✅ **支持撤销和过期**：灵活的生命周期管理

---

## 第三层：文档级 ACL

### 文档 ACL 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `sensitivity_level` | String | 敏感度级别：public/restricted |
| `acl_allow_users` | JSON | 允许访问的用户 ID 列表 |
| `acl_allow_roles` | JSON | 允许访问的角色列表 |
| `acl_allow_groups` | JSON | 允许访问的组/部门列表 |

### 敏感度级别

| 级别 | 说明 | 访问规则 |
|------|------|---------|
| **public** | 公开文档 | 租户内所有 API Key 可访问 |
| **restricted** | 受限文档 | 需要 ACL 白名单匹配 + 敏感度级别够 |

**向后兼容**：旧版的 `internal/confidential/secret` 会被视为 `restricted` 处理。

### 用户身份上下文

API Key 的 `identity` 字段定义用户身份信息：

```json
{
  "user_id": "zhang_san",
  "roles": ["sales", "viewer"],
  "groups": ["dept_sales"],
  "clearance": "restricted"
}
```

| 字段 | 说明 |
|------|------|
| `user_id` | 用户 ID（匹配 `acl_allow_users`） |
| `roles` | 用户角色列表（匹配 `acl_allow_roles`） |
| `groups` | 用户所属组/部门（匹配 `acl_allow_groups`） |
| `clearance` | 敏感度访问级别：public/restricted |

### ACL 访问规则

```
1. 管理员（API Key role=admin）→ 可访问所有文档

2. public 文档 → 所有人可访问

3. restricted 文档 → 需要同时满足：
   a) 用户 clearance = "restricted"
   b) 匹配 ACL 白名单（users/roles/groups 任一）
```

### 创建带 ACL 的文档

```bash
curl -X POST -H "Authorization: Bearer kb_sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "内部财务报告",
    "content": "...",
    "sensitivity_level": "restricted",
    "acl_allow_roles": ["finance", "executive"],
    "acl_allow_groups": ["dept_finance"]
  }' \
  "http://localhost:8020/v1/knowledge-bases/{kb_id}/documents"
```

### 创建带身份信息的 API Key

```bash
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "财务部门Key",
    "role": "read",
    "identity": {
      "user_id": "finance_user_001",
      "roles": ["finance", "viewer"],
      "groups": ["dept_finance"],
      "clearance": "restricted"
    }
  }' \
  "http://localhost:8020/v1/api-keys"
```

### Security Trimming 实现

检索时自动过滤无权限文档，采用**两阶段过滤**：

#### 阶段1：向量库层面过滤（性能优化）

在向量检索时添加过滤条件，减少无效检索：

```python
# Qdrant Filter 示例
{
  "should": [
    {"key": "sensitivity_level", "match": {"value": "public"}},
    {"key": "acl_users", "match": {"any": ["zhang_san"]}},
    {"key": "acl_roles", "match": {"any": ["sales", "viewer"]}},
    {"key": "acl_groups", "match": {"any": ["dept_sales"]}}
  ]
}
```

#### 阶段2：应用层二次过滤（安全兜底）

检索结果返回前再次检查 ACL，确保安全：

```python
def filter_results_by_acl(results: list[dict], user: UserContext) -> list[dict]:
    """后处理：根据 ACL 过滤检索结果"""
    if user.is_admin:
        return results
    
    filtered = []
    for result in results:
        if check_document_access(user, doc_acl):
            filtered.append(result)
    
    return filtered
```

### ACL 过滤错误处理

如果检索结果被 ACL 全部过滤，返回 403 错误：

```json
{
  "code": "NO_PERMISSION",
  "detail": "All retrieved documents were filtered by ACL"
}
```

**排查步骤**：
1. 检查 API Key 的 `identity` 字段是否正确
2. 检查文档的 `sensitivity_level` 和 ACL 白名单
3. 确认用户的 `clearance` 级别是否足够

---

## 认证与授权流程

### 完整请求流程

```
1. 请求到达
   ↓
   Authorization: Bearer kb_sk_xxxxxxxx
   
2. API Key 认证
   ↓
   - 提取 Bearer Token
   - SHA256 哈希
   - 查询数据库匹配
   - 检查是否过期/撤销
   ↓
   返回 APIKeyContext(api_key, tenant)
   
3. 租户状态检查
   ↓
   tenant.status == "active"?
   ├─ Yes → 继续
   └─ No → 403 TENANT_DISABLED
   
4. 限流检查
   ↓
   rate_limiter.allow()?
   ├─ 通过 → 继续
   └─ 超限 → 429 RATE_LIMIT_EXCEEDED
   
5. 角色权限检查
   ↓
   require_role("admin", "write")?
   ├─ 匹配 → 继续
   └─ 不匹配 → 403 ROLE_NOT_ALLOWED
   
6. KB 白名单检查
   ↓
   scope_kb_ids 包含请求的 KB?
   ├─ 包含或为空 → 继续
   └─ 不包含 → 403 KB_ACCESS_DENIED
   
7. 执行业务逻辑
   ↓
   检索/上传文档等
   
8. ACL 过滤
   ↓
   - 向量库层面过滤
   - 应用层二次过滤
   
9. 返回结果
   ↓
   只包含有权限的文档
```

### 认证错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| `UNAUTHORIZED` | 401 | 缺少或无效的 Authorization 头 |
| `INVALID_API_KEY` | 401 | API Key 无效或已过期 |
| `TENANT_DISABLED` | 403 | 租户已禁用 |
| `ROLE_NOT_ALLOWED` | 403 | 角色权限不足 |
| `KB_ACCESS_DENIED` | 403 | KB 访问被拒绝（白名单） |
| `NO_PERMISSION` | 403 | 文档 ACL 过滤（无权限） |
| `RATE_LIMIT_EXCEEDED` | 429 | 超过限流限制 |

---

## 限流机制

### 限流器类型

| 类型 | 适用场景 | 存储方式 |
|------|---------|---------|
| **MemoryRateLimiter** | 单实例部署 | 内存滑动窗口 |
| **RedisRateLimiter** | 多实例部署 | Redis Sorted Set |

系统会根据 `REDIS_URL` 环境变量自动选择限流器。

### 限流配置

#### 全局默认限流

```bash
# 环境变量
API_RATE_LIMIT_PER_MINUTE=120
API_RATE_LIMIT_WINDOW_SECONDS=60
```

#### API Key 级别限流

创建 API Key 时设置独立限流：

```bash
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "高频调用Key",
    "role": "read",
    "rate_limit_per_minute": 300
  }' \
  "http://localhost:8020/v1/api-keys"
```

### 限流降级

Redis 限流器异常时自动降级到允许通过，确保服务可用性。

---

## 最佳实践

### 1. 租户级别

```python
# 创建租户时设置合理配额
tenant = {
    "name": "企业A",
    "status": "active",
    "quota_kb_count": 10,      # 最多 10 个知识库
    "quota_doc_count": 1000,   # 最多 1000 个文档
    "quota_storage_mb": 5120,  # 最多 5GB 存储
}
```

### 2. API Key 级别

#### 场景1：客服系统只读访问

```json
{
  "name": "客服系统只读Key",
  "role": "read",
  "scope_kb_ids": ["kb_product_manual", "kb_faq"],
  "identity": {
    "user_id": "customer_service_bot",
    "roles": ["viewer"],
    "clearance": "public"
  }
}
```

#### 场景2：内容管理员

```json
{
  "name": "内容管理员Key",
  "role": "write",
  "identity": {
    "user_id": "content_admin_001",
    "roles": ["editor", "admin"],
    "clearance": "restricted"
  }
}
```

#### 场景3：外部合作伙伴

```json
{
  "name": "合作伙伴API",
  "role": "read",
  "scope_kb_ids": ["kb_public_docs"],
  "rate_limit_per_minute": 60,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### 3. 文档级别

#### 公开文档

```json
{
  "title": "产品使用手册",
  "sensitivity_level": "public"
}
```

#### 部门受限文档

```json
{
  "title": "销售培训资料",
  "sensitivity_level": "restricted",
  "acl_allow_groups": ["dept_sales"]
}
```

#### 角色受限文档

```json
{
  "title": "财务报告",
  "sensitivity_level": "restricted",
  "acl_allow_roles": ["finance", "executive"]
}
```

#### 个人受限文档

```json
{
  "title": "个人绩效评估",
  "sensitivity_level": "restricted",
  "acl_allow_users": ["zhang_san", "hr_manager"]
}
```

---

## 常见问题

### Q1: 如何创建租户的第一个 API Key？

**A**: 使用 Admin API 创建租户时会自动生成初始管理员 Key：

```bash
curl -X POST -H "X-Admin-Token: your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "企业A"}' \
  "http://localhost:8020/admin/tenants"
```

响应中会包含初始 API Key（仅显示一次）：

```json
{
  "tenant": {...},
  "initial_api_key": "kb_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### Q2: API Key 丢失了怎么办？

**A**: API Key 明文仅在创建时显示一次，无法恢复。需要：
1. 使用管理员 Key 创建新的 API Key
2. 撤销旧的 API Key（如果担心泄露）

```bash
# 创建新 Key
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -d '{"name": "新的管理员Key", "role": "admin"}' \
  "http://localhost:8020/v1/api-keys"

# 撤销旧 Key
curl -X DELETE -H "Authorization: Bearer kb_sk_admin_key" \
  "http://localhost:8020/v1/api-keys/{old_key_id}"
```

### Q3: 检索结果为空，但知道文档存在？

**A**: 可能是 ACL 过滤导致。检查步骤：

1. **确认 API Key 的 identity 字段**：
```bash
curl -H "Authorization: Bearer kb_sk_xxx" \
  "http://localhost:8020/v1/api-keys"
```

2. **确认文档的 ACL 配置**：
```bash
curl -H "Authorization: Bearer kb_sk_xxx" \
  "http://localhost:8020/v1/knowledge-bases/{kb_id}/documents/{doc_id}"
```

3. **检查是否返回 403 错误**：
```json
{
  "code": "NO_PERMISSION",
  "detail": "All retrieved documents were filtered by ACL"
}
```

4. **解决方案**：
   - 更新 API Key 的 `identity.clearance` 为 `"restricted"`
   - 将用户添加到文档的 ACL 白名单
   - 或将文档的 `sensitivity_level` 改为 `"public"`

### Q4: 如何实现部门级权限隔离？

**A**: 使用 `identity.groups` + 文档 `acl_allow_groups`：

```bash
# 1. 创建部门 API Key
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -d '{
    "name": "销售部Key",
    "role": "read",
    "identity": {
      "groups": ["dept_sales"],
      "clearance": "restricted"
    }
  }' \
  "http://localhost:8020/v1/api-keys"

# 2. 上传部门文档
curl -X POST -H "Authorization: Bearer kb_sk_xxx" \
  -d '{
    "title": "销售培训资料",
    "content": "...",
    "sensitivity_level": "restricted",
    "acl_allow_groups": ["dept_sales"]
  }' \
  "http://localhost:8020/v1/knowledge-bases/{kb_id}/documents"
```

### Q5: 如何限制 API Key 只能访问特定知识库？

**A**: 使用 `scope_kb_ids` 字段：

```bash
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -d '{
    "name": "产品文档访问Key",
    "role": "read",
    "scope_kb_ids": ["kb_product_manual", "kb_faq"]
  }' \
  "http://localhost:8020/v1/api-keys"
```

尝试访问其他 KB 会返回 403 错误。

### Q6: 如何禁用租户？

**A**: 使用 Admin API：

```bash
curl -X POST -H "X-Admin-Token: your-admin-token" \
  -d '{"reason": "欠费停用"}' \
  "http://localhost:8020/admin/tenants/{tenant_id}/disable"
```

禁用后，该租户的所有 API Key 立即失效。

### Q7: 如何设置 API Key 过期时间？

**A**: 创建时指定 `expires_at`：

```bash
curl -X POST -H "Authorization: Bearer kb_sk_admin_key" \
  -d '{
    "name": "临时访问Key",
    "role": "read",
    "expires_at": "2026-12-31T23:59:59Z"
  }' \
  "http://localhost:8020/v1/api-keys"
```

### Q8: 如何查看 API Key 的使用情况？

**A**: 查看 `last_used_at` 字段：

```bash
curl -H "Authorization: Bearer kb_sk_admin_key" \
  "http://localhost:8020/v1/api-keys"
```

响应：
```json
{
  "items": [
    {
      "id": "xxx",
      "name": "客服系统Key",
      "last_used_at": "2026-01-26T02:30:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

## 相关文档

- [API 对接文档](./api-integration.md)
- [模型配置文档](./api-integration.md#7-模型配置优先级)
- [部署文档](../operations/deployment.md)

---

## 技术支持

如有问题，请提交 Issue 或联系技术支持团队。
