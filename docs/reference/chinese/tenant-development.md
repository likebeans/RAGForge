# 租户管理系统

> **状态**: Phase 1-5 已完成 ✅，Phase 6 (CLI) 待实现

## 概述

租户管理系统提供完整的多租户生命周期管理功能，包括：
- **租户 CRUD**: 创建、查询、更新、禁用/启用、删除
- **API Key 管理**: 支持 admin/write/read 三种角色
- **权限控制**: 基于角色的访问控制和租户状态检查
- **管理员接口**: 通过 Admin Token 认证的管理 API

## 快速开始

### 1. 配置 Admin Token

```bash
# .env 或环境变量
ADMIN_TOKEN=your-secure-admin-token
```

### 2. 创建租户

```bash
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-company", "plan": "standard"}'
```

响应包含初始 admin API Key（仅显示一次）:
```json
{
  "id": "xxx-xxx-xxx",
  "name": "my-company",
  "status": "active",
  "initial_api_key": "kb_sk_xxxxxxxxx"
}
```

### 3. 使用 API Key

```bash
curl http://localhost:8020/v1/knowledge-bases \
  -H "Authorization: Bearer kb_sk_xxxxxxxxx"
```

---

## Phase 1: 数据模型增强 ✅

> 文件位置: `app/models/tenant.py`, `app/models/api_key.py`, `app/models/usage_log.py`

### 1.1 Tenant 模型

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | `String(36)` | UUID | 主键 |
| `name` | `String(255)` | - | 租户名称（唯一） |
| `plan` | `String(50)` | `"standard"` | 订阅计划 |
| `status` | `String(20)` | `"active"` | 状态: active/disabled/pending |
| `quota_kb_count` | `Integer` | `10` | 知识库数量限制，-1=无限 |
| `quota_doc_count` | `Integer` | `1000` | 文档数量限制，-1=无限 |
| `quota_storage_mb` | `Integer` | `1024` | 存储限制(MB)，-1=无限 |
| `disabled_at` | `DateTime` | `None` | 禁用时间 |
| `disabled_reason` | `Text` | `None` | 禁用原因 |

### 1.2 APIKey 模型

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `role` | `String(20)` | `"write"` | 角色: admin/write/read |
| `scope_kb_ids` | `JSON` | `None` | KB 白名单，null=全部 |
| `is_initial` | `Boolean` | `False` | 是否为初始管理员 Key |
| `description` | `Text` | `None` | 描述/备注 |

### 1.3 UsageLog 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键 |
| `tenant_id` | `String(36)` | 租户 ID (FK) |
| `api_key_id` | `String(36)` | API Key ID (FK, 可空) |
| `action` | `String(50)` | 操作类型 |
| `resource_type` | `String(50)` | 资源类型 |
| `resource_id` | `String(36)` | 资源 ID |
| `details` | `JSON` | 额外信息 |
| `created_at` | `DateTime` | 创建时间 |

### 1.4 数据库迁移

迁移文件: `alembic/versions/4bfb74f0f2d5_add_tenant_management_fields.py`

```bash
# 在 Docker 容器中执行
docker compose exec api uv run alembic upgrade head
```

---

## Phase 2: 管理员认证 ✅

> 文件位置: `app/config.py`, `app/api/deps.py`

### 2.1 配置

```python
# app/config.py
admin_token: str | None = None  # 管理员 Token，通过 ADMIN_TOKEN 环境变量设置
```

Docker Compose 配置:
```yaml
# docker-compose.yml
environment:
  ADMIN_TOKEN: ${ADMIN_TOKEN:-}
```

### 2.2 认证依赖

```python
# app/api/deps.py
async def verify_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> str:
    """验证管理员 Token，通过 X-Admin-Token 请求头传递"""
```

错误响应:
- `503`: Admin API 未配置（未设置 ADMIN_TOKEN）
- `401`: 缺少 X-Admin-Token 头
- `403`: Token 无效

---

## Phase 3: 租户管理 API ✅

> 文件位置: `app/api/routes/admin.py`, `app/schemas/tenant.py`

### 3.1 API 端点

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| `POST` | `/admin/tenants` | 创建租户（返回初始 admin Key） | ✅ |
| `GET` | `/admin/tenants` | 列出所有租户（分页、状态过滤） | ✅ |
| `GET` | `/admin/tenants/{id}` | 租户详情（含 KB 统计） | ✅ |
| `PATCH` | `/admin/tenants/{id}` | 更新租户信息 | ✅ |
| `POST` | `/admin/tenants/{id}/disable` | 禁用租户 | ✅ |
| `POST` | `/admin/tenants/{id}/enable` | 启用租户 | ✅ |
| `DELETE` | `/admin/tenants/{id}` | 删除租户（级联删除） | ✅ |
| `GET` | `/admin/tenants/{id}/api-keys` | 列出租户的 Keys | ✅ |
| `POST` | `/admin/tenants/{id}/api-keys` | 为租户创建 Key | ✅ |
| `DELETE` | `/admin/tenants/{id}/api-keys/{key_id}` | 删除 API Key | ✅ |

### 3.2 创建租户

**请求:**
```bash
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-company",
    "plan": "standard",
    "quota_kb_count": 10,
    "quota_doc_count": 1000,
    "quota_storage_mb": 1024
  }'
```

**响应:**
```json
{
  "id": "c9766e90-0837-4db9-8529-1d8e2e6f22d3",
  "name": "my-company",
  "plan": "standard",
  "status": "active",
  "quota_kb_count": 10,
  "quota_doc_count": 1000,
  "quota_storage_mb": 1024,
  "created_at": "2025-12-03T07:04:21.148387Z",
  "updated_at": "2025-12-03T07:04:21.148387Z",
  "disabled_at": null,
  "disabled_reason": null,
  "initial_api_key": "kb_sk_z59p6PmCsxTMfVOP0HdXOMZt1jKl4gNDZrqYsyD1QTM"
}
```

> ⚠️ `initial_api_key` 仅在创建时返回一次，请妥善保管

### 3.3 禁用/启用租户

```bash
# 禁用
curl -X POST http://localhost:8020/admin/tenants/{id}/disable \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Payment overdue"}'

# 启用
curl -X POST http://localhost:8020/admin/tenants/{id}/enable \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

### 3.4 为租户创建 API Key

```bash
curl -X POST http://localhost:8020/admin/tenants/{id}/api-keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "readonly-key",
    "role": "read",
    "description": "For external integration"
  }'
```

---

## Phase 4: API Key 权限校验 ✅

> 文件位置: `app/api/deps.py`

### 4.1 权限矩阵

| 操作 | admin | write | read |
|------|:-----:|:-----:|:----:|
| 管理 API Key | ✅ | ❌ | ❌ |
| 创建知识库 | ✅ | ✅ | ❌ |
| 删除知识库 | ✅ | ✅ | ❌ |
| 上传文档 | ✅ | ✅ | ❌ |
| 删除文档 | ✅ | ✅ | ❌ |
| 检索 | ✅ | ✅ | ✅ |
| 列出知识库 | ✅ | ✅ | ✅ |
| 列出文档 | ✅ | ✅ | ✅ |

### 4.2 角色检查依赖

```python
# app/api/deps.py
def require_role(*allowed_roles: Literal["admin", "write", "read"]):
    """创建角色权限检查依赖"""
    async def check_role(context: APIKeyContext = Depends(get_api_key_context)) -> APIKeyContext:
        # 检查租户状态
        if context.tenant.status != "active":
            raise HTTPException(403, f"Tenant is {context.tenant.status}")
        # 检查角色权限
        if context.api_key.role not in allowed_roles:
            raise HTTPException(403, f"Role '{context.api_key.role}' not allowed")
        return context
    return check_role

# 使用示例
@router.post("/knowledge-bases")
async def create_kb(context: APIKeyContext = Depends(require_role("admin", "write"))):
    pass
```

---

## Phase 5: 租户状态校验 ✅

> 文件位置: `app/auth/api_key.py`

### 5.1 禁用租户拦截

在 `get_api_key_context` 中添加租户状态检查：

```python
# app/auth/api_key.py
async def get_api_key_context(...) -> APIKeyContext:
    # ... API Key 验证 ...
    
    # 检查租户状态
    if tenant.status != "active":
        raise HTTPException(
            status_code=403,
            detail={"code": "TENANT_DISABLED", "detail": f"Tenant is {tenant.status}"}
        )
    
    return APIKeyContext(api_key=api_key, tenant=tenant)
```

### 5.2 错误响应示例

当租户被禁用时，所有 API Key 请求返回:
```json
{
  "code": "TENANT_DISABLED",
  "detail": "Tenant is disabled"
}
```

---

## Phase 6: CLI 初始化命令 ⏳

> 状态: 待实现

CLI 命令作为 Admin API 的替代方案，适用于无法访问 HTTP 接口的场景。

### 6.1 计划命令

```bash
# 初始化第一个租户
uv run python -m app.cli init --name "my-company" --plan "enterprise"

# 输出示例
# ✅ 租户创建成功
# 租户 ID: xxx-xxx-xxx
# 初始 API Key: kb_sk_xxxxxxxxx
# ⚠️  请妥善保存此 Key，它不会再次显示
```

### 6.2 临时替代方案

在 CLI 实现前，可直接使用 Admin API:

```bash
# 启动时设置 ADMIN_TOKEN
ADMIN_TOKEN=my-secret-token docker compose up -d

# 使用 curl 创建租户
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: my-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-company"}'
```

---

## 实施进度

| 步骤 | 内容 | 状态 |
|------|------|:----:|
| Step 1 | 模型和迁移 | ✅ |
| Step 2 | 配置和认证 | ✅ |
| Step 3 | Pydantic Schema | ✅ |
| Step 4 | Admin API 路由 | ✅ |
| Step 5 | 权限校验 | ✅ |
| Step 6 | CLI 命令 | ⏳ |
| Step 7 | 测试和文档 | ✅ |

### 已完成文件

| 文件 | 说明 |
|------|------|
| `app/models/tenant.py` | Tenant 模型扩展 |
| `app/models/api_key.py` | APIKey 模型扩展 |
| `app/models/usage_log.py` | UsageLog 模型（新建） |
| `app/config.py` | 添加 `admin_token` 配置 |
| `app/api/deps.py` | 添加 `verify_admin_token`, `require_role` |
| `app/api/routes/admin.py` | Admin API 路由（新建） |
| `app/schemas/tenant.py` | Tenant Schema（新建） |
| `app/schemas/api_key.py` | APIKey Schema 扩展 |
| `app/auth/api_key.py` | 添加租户状态检查 |
| `alembic/versions/4bfb74f0f2d5_*.py` | 数据库迁移 |

---

## 测试验证

### 已验证功能

| 测试项 | 结果 |
|--------|:----:|
| Admin Token 认证 | ✅ |
| 创建租户 + 初始 API Key | ✅ |
| 列出/查询租户 | ✅ |
| 更新租户信息 | ✅ |
| 禁用租户 | ✅ |
| 禁用后 API Key 被拒绝 (403) | ✅ |
| 启用租户后恢复访问 | ✅ |
| 删除租户 | ✅ |
| 创建/列出租户 API Key | ✅ |

### 测试命令

```bash
# 设置环境
export ADMIN_TOKEN="test-admin-token"
export API_BASE="http://localhost:8020"

# 1. 创建租户
TENANT=$(curl -s -X POST "$API_BASE/admin/tenants" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-tenant"}')
TENANT_ID=$(echo $TENANT | jq -r '.id')
API_KEY=$(echo $TENANT | jq -r '.initial_api_key')

# 2. 测试 API Key
curl -s "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"
# 应返回: {"items":[],"total":0,...}

# 3. 禁用租户
curl -s -X POST "$API_BASE/admin/tenants/$TENANT_ID/disable" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test"}'

# 4. 测试禁用后访问
curl -s "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"
# 应返回: {"code":"TENANT_DISABLED","detail":"Tenant is disabled"}

# 5. 启用租户
curl -s -X POST "$API_BASE/admin/tenants/$TENANT_ID/enable" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# 6. 测试恢复访问
curl -s "$API_BASE/v1/knowledge-bases" \
  -H "Authorization: Bearer $API_KEY"
# 应返回: {"items":[],"total":0,...}
```

---

## 后续扩展（不在本次范围）

- **用量统计**: `GET /admin/tenants/{id}/usage` - 查询租户 API 调用统计
- **配额检查**: 在创建 KB/文档时检查 quota 限制
- **审计日志**: 记录所有 API 操作到 usage_logs 表
- **计费集成**: 基于用量的计费系统
- **自助注册**: 租户自主注册流程
- **WebSocket**: 实时通知和事件推送
