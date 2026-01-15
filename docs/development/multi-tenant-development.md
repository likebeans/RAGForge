# 多租户开发指南

本文档介绍多租户管理系统的开发和使用，包括租户生命周期管理、API Key 权限控制和管理员接口。

## 系统概述

Self-RAG Pipeline 采用多租户架构，提供完整的租户隔离和权限管理功能：

- **租户 CRUD**：创建、查询、更新、禁用/启用、删除
- **API Key 管理**：支持 admin/write/read 三种角色
- **权限控制**：基于角色的访问控制和租户状态检查
- **管理员接口**：通过 Admin Token 认证的管理 API
- **数据隔离**：租户间数据完全隔离，支持多种向量存储隔离策略

## 快速开始

### 1. 配置管理员令牌

在环境变量或 `.env` 文件中设置管理员令牌：

```bash
ADMIN_TOKEN=your-secure-admin-token
```

### 2. 创建第一个租户

```bash
curl -X POST http://localhost:8020/admin/tenants \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-company", "plan": "standard"}'
```

响应包含初始 admin API Key（仅显示一次）：
```json
{
  "id": "xxx-xxx-xxx",
  "name": "my-company",
  "status": "active",
  "initial_api_key": "kb_sk_xxxxxxxxx"
}
```

### 3. 使用 API Key 访问服务

```bash
curl http://localhost:8020/v1/knowledge-bases \
  -H "Authorization: Bearer kb_sk_xxxxxxxxx"
```

## 数据模型

### 租户模型 (Tenant)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | `String(36)` | UUID | 主键 |
| `name` | `String(255)` | - | 租户名称（唯一） |
| `plan` | `String(50)` | `"standard"` | 订阅计划 |
| `status` | `String(20)` | `"active"` | 状态: active/disabled/pending |
| `quota_kb_count` | `Integer` | `10` | 知识库数量限制，-1=无限 |
| `quota_doc_count` | `Integer` | `1000` | 文档数量限制，-1=无限 |
| `quota_storage_mb` | `Integer` | `1024` | 存储限制(MB)，-1=无限 |
| `isolation_strategy` | `String(20)` | `"auto"` | 向量存储隔离策略 |
| `model_config` | `JSON` | `{}` | 租户级模型配置 |
| `disabled_at` | `DateTime` | `None` | 禁用时间 |
| `disabled_reason` | `Text` | `None` | 禁用原因 |

### API Key 模型 (APIKey)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | `String(36)` | UUID | 主键 |
| `tenant_id` | `String(36)` | - | 所属租户 ID |
| `name` | `String(255)` | - | API Key 名称 |
| `key_hash` | `String(64)` | - | SHA256 哈希值 |
| `prefix` | `String(10)` | - | 前缀（用于识别） |
| `role` | `String(20)` | `"write"` | 角色: admin/write/read |
| `scope_kb_ids` | `JSON` | `None` | KB 白名单，null=全部 |
| `identity` | `JSON` | `None` | 用户身份信息（用于 ACL） |
| `is_initial` | `Boolean` | `False` | 是否为初始管理员 Key |
| `description` | `Text` | `None` | 描述/备注 |

### 使用日志模型 (UsageLog)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键 |
| `tenant_id` | `String(36)` | 租户 ID |
| `api_key_id` | `String(36)` | API Key ID（可空） |
| `action` | `String(50)` | 操作类型 |
| `resource_type` | `String(50)` | 资源类型 |
| `resource_id` | `String(36)` | 资源 ID |
| `details` | `JSON` | 额外信息 |
| `created_at` | `DateTime` | 创建时间 |

## 管理员 API

### 认证方式

所有管理员 API 使用 `X-Admin-Token` 请求头进行认证：

```bash
curl -H "X-Admin-Token: your-admin-token" \
  http://localhost:8020/admin/tenants
```

### 租户管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/admin/tenants` | 创建租户（返回初始 admin Key） |
| `GET` | `/admin/tenants` | 列出所有租户（分页、状态过滤） |
| `GET` | `/admin/tenants/{id}` | 租户详情（含 KB 统计） |
| `PATCH` | `/admin/tenants/{id}` | 更新租户信息 |
| `POST` | `/admin/tenants/{id}/disable` | 禁用租户 |
| `POST` | `/admin/tenants/{id}/enable` | 启用租户 |
| `DELETE` | `/admin/tenants/{id}` | 删除租户（级联删除） |

### API Key 管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/tenants/{id}/api-keys` | 列出租户的 API Keys |
| `POST` | `/admin/tenants/{id}/api-keys` | 为租户创建 API Key |
| `DELETE` | `/admin/tenants/{id}/api-keys/{key_id}` | 删除 API Key |

## 权限系统

### 角色权限矩阵

| 操作 | admin | write | read |
|------|:-----:|:-----:|:----:|
| 管理 API Key | ✅ | ❌ | ❌ |
| 创建知识库 | ✅ | ✅ | ❌ |
| 删除知识库 | ✅ | ✅ | ❌ |
| 上传文档 | ✅ | ✅ | ❌ |
| 删除文档 | ✅ | ✅ | ❌ |
| 检索查询 | ✅ | ✅ | ✅ |
| 列出知识库 | ✅ | ✅ | ✅ |
| 列出文档 | ✅ | ✅ | ✅ |

### 权限检查实现

```python
from app.api.deps import require_role

# 需要 admin 权限的操作
@router.post("/v1/api-keys")
async def create_api_key(
    context: APIKeyContext = Depends(require_role("admin"))
):
    pass

# 需要 admin 或 write 权限的操作
@router.post("/v1/knowledge-bases")
async def create_kb(
    context: APIKeyContext = Depends(require_role("admin", "write"))
):
    pass

# 所有角色都可以访问的操作
@router.get("/v1/knowledge-bases")
async def list_kbs(
    context: APIKeyContext = Depends(get_current_api_key)
):
    pass
```

### KB 白名单 (scope_kb_ids)

API Key 可以限制只能访问特定的知识库：

```bash
# 创建只能访问特定 KB 的 API Key
curl -X POST "/admin/tenants/{id}/api-keys" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "limited-access-key",
    "role": "read",
    "scope_kb_ids": ["kb-id-1", "kb-id-2"]
  }'
```

当 API Key 设置了 `scope_kb_ids` 时，只能访问白名单中的知识库，访问其他 KB 会返回 403 错误。

## 向量存储隔离策略

系统支持三种多租户隔离策略：

| 模式 | Collection 名称 | 隔离方式 | 适用场景 |
|------|----------------|---------|---------|
| **Partition** | `kb_shared` | 通过 `kb_id` 字段过滤 | 小规模、资源共享（默认） |
| **Collection** | `kb_{tenant_id}` | 每租户独立 Collection | 大规模、高性能需求 |
| **Auto** | 自动选择 | 根据数据量自动切换 | 自动优化、平衡成本 |

### 配置隔离策略

**方式 1：环境变量**
```bash
QDRANT_ISOLATION_STRATEGY=partition  # 或 collection、auto
```

**方式 2：Admin API**
```bash
curl -X PATCH "/admin/tenants/{id}" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"isolation_strategy": "collection"}'
```

### 隔离策略切换注意事项

1. 切换模式不会自动迁移已有数据
2. 入库和检索必须使用相同的隔离模式
3. 建议在租户创建时确定隔离策略

## 租户状态管理

### 禁用租户

```bash
curl -X POST "/admin/tenants/{id}/disable" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Payment overdue"}'
```

禁用后，该租户的所有 API Key 将被拒绝访问，返回 403 错误：
```json
{
  "code": "TENANT_DISABLED",
  "detail": "Tenant is disabled"
}
```

### 启用租户

```bash
curl -X POST "/admin/tenants/{id}/enable" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

启用后，租户的 API Key 恢复正常访问。

## 开发指南

### 添加新的租户级配置

1. **更新数据模型**：
   ```python
   # app/models/tenant.py
   class Tenant(Base):
       # 添加新字段
       new_config: Mapped[dict | None] = mapped_column(JSON, default=dict)
   ```

2. **创建数据库迁移**：
   ```bash
   uv run alembic revision --autogenerate -m "add tenant new_config"
   uv run alembic upgrade head
   ```

3. **更新 Schema**：
   ```python
   # app/schemas/tenant.py
   class TenantUpdate(BaseModel):
       new_config: dict | None = None
   
   class TenantResponse(BaseModel):
       new_config: dict
   ```

4. **更新 API 路由**：
   ```python
   # app/api/routes/admin.py
   @router.patch("/admin/tenants/{tenant_id}")
   async def update_tenant(
       tenant_id: str,
       payload: TenantUpdate,
       # ...
   ):
       if payload.new_config is not None:
           tenant.new_config = payload.new_config
   ```

### 添加新的权限检查

1. **定义权限常量**：
   ```python
   # app/auth/permissions.py
   class Permission:
       MANAGE_USERS = "manage_users"
       VIEW_ANALYTICS = "view_analytics"
   ```

2. **实现权限检查函数**：
   ```python
   def require_permission(permission: str):
       async def check_permission(
           context: APIKeyContext = Depends(get_current_api_key)
       ) -> APIKeyContext:
           if not has_permission(context.api_key, permission):
               raise HTTPException(403, "Permission denied")
           return context
       return check_permission
   ```

3. **在路由中使用**：
   ```python
   @router.get("/admin/analytics")
   async def get_analytics(
       context: APIKeyContext = Depends(require_permission("view_analytics"))
   ):
       pass
   ```

### 实现租户级资源配额

1. **检查配额函数**：
   ```python
   async def check_kb_quota(tenant: Tenant, session: AsyncSession) -> None:
       if tenant.quota_kb_count == -1:  # 无限制
           return
       
       current_count = await session.scalar(
           select(func.count(KnowledgeBase.id))
           .where(KnowledgeBase.tenant_id == tenant.id)
       )
       
       if current_count >= tenant.quota_kb_count:
           raise HTTPException(403, "Knowledge base quota exceeded")
   ```

2. **在创建资源时调用**：
   ```python
   @router.post("/v1/knowledge-bases")
   async def create_kb(
       payload: KBCreate,
       context: APIKeyContext = Depends(require_role("admin", "write")),
       session: AsyncSession = Depends(get_db_session),
   ):
       await check_kb_quota(context.tenant, session)
       # 创建知识库...
   ```

## 测试指南

### 多租户隔离测试

```python
import pytest
from app.tests.conftest import TestClient

async def test_tenant_isolation():
    # 创建两个租户
    tenant_a = await create_test_tenant("tenant-a")
    tenant_b = await create_test_tenant("tenant-b")
    
    # 租户 A 创建知识库
    kb_a = await create_kb(tenant_a.api_key, "KB A")
    
    # 租户 B 尝试访问租户 A 的知识库（应该失败）
    response = await client.get(
        f"/v1/knowledge-bases/{kb_a.id}",
        headers={"Authorization": f"Bearer {tenant_b.api_key}"}
    )
    assert response.status_code == 404
```

### 权限测试

```python
async def test_role_permissions():
    tenant = await create_test_tenant("test-tenant")
    
    # 创建不同角色的 API Key
    admin_key = tenant.initial_api_key  # admin 角色
    read_key = await create_api_key(admin_key, "read-key", role="read")
    
    # admin 可以创建知识库
    response = await client.post(
        "/v1/knowledge-bases",
        headers={"Authorization": f"Bearer {admin_key}"},
        json={"name": "Test KB"}
    )
    assert response.status_code == 201
    
    # read 角色不能创建知识库
    response = await client.post(
        "/v1/knowledge-bases",
        headers={"Authorization": f"Bearer {read_key}"},
        json={"name": "Test KB 2"}
    )
    assert response.status_code == 403
```

## 安全注意事项

### API Key 安全

- API Key 使用 SHA256 哈希存储，不保存明文
- 初始 API Key 仅在创建时返回一次，请妥善保管
- 定期轮换 API Key，特别是 admin 角色的 Key
- 使用 `scope_kb_ids` 限制 API Key 的访问范围

### 管理员令牌安全

- 管理员令牌应使用强随机字符串
- 定期更换管理员令牌
- 限制管理员令牌的网络访问（如仅内网访问）
- 记录所有管理员操作的审计日志

### 租户隔离

- 所有数据表必须包含 `tenant_id` 字段
- 查询时强制过滤 `tenant_id`
- 向量库按租户隔离，防止数据泄露
- 定期审计跨租户访问日志

## 监控和运维

### 关键指标

- 租户数量和状态分布
- API Key 使用频率和错误率
- 跨租户访问尝试（安全事件）
- 资源配额使用情况

### 日志记录

系统自动记录以下操作到审计日志：

- 租户创建/禁用/删除
- API Key 创建/撤销/轮换
- 跨租户访问尝试
- 权限检查失败

### 故障排查

**常见问题**：

1. **租户无法访问**
   - 检查租户状态是否为 active
   - 验证 API Key 是否有效
   - 确认权限角色是否正确

2. **跨租户数据泄露**
   - 检查查询是否包含 tenant_id 过滤
   - 验证向量库隔离配置
   - 审查 API Key 的 scope_kb_ids 设置

3. **性能问题**
   - 监控数据库连接池使用情况
   - 检查向量库 Collection 数量
   - 优化频繁查询的索引

## 最佳实践

### 租户管理

1. **命名规范**：使用有意义的租户名称，如公司域名
2. **配额设置**：根据业务需求合理设置资源配额
3. **隔离策略**：小租户使用 Partition，大租户使用 Collection
4. **生命周期管理**：定期清理不活跃的租户

### API Key 管理

1. **最小权限原则**：只授予必要的权限
2. **定期轮换**：建议每 90 天轮换一次 API Key
3. **范围限制**：使用 `scope_kb_ids` 限制访问范围
4. **监控使用**：跟踪 API Key 的使用情况和异常访问

### 安全防护

1. **访问控制**：使用防火墙限制管理员 API 的访问
2. **审计日志**：定期审查访问日志和安全事件
3. **备份恢复**：定期备份租户数据和配置
4. **应急响应**：制定安全事件的应急响应流程

通过遵循这些指南，可以安全、高效地开发和维护多租户系统。