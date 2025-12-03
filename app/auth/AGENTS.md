# Auth 认证模块

API Key 认证、角色权限和租户状态控制。

## 模块职责

- API Key 生成和验证
- 请求限流（Rate Limiting）
- 租户身份识别和状态检查
- 角色权限控制（admin/write/read）

## 核心文件

| 文件 | 说明 |
|------|------|
| `api_key.py` | API Key 认证逻辑、限流器、租户状态检查 |

## API Key 设计

### 存储方式
- 明文 Key 仅在创建时返回一次
- 数据库存储 SHA256 哈希值
- 验证时对比哈希值

### Key 格式
```
kb_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 角色权限

| 角色 | 说明 |
|------|------|
| `admin` | 全部权限 + 管理 API Key |
| `write` | 创建/删除 KB、上传文档、检索 |
| `read` | 仅检索和列表 |

## 认证流程

```
请求 → Authorization Header → 提取 Bearer Token → SHA256 哈希 
    → 查询数据库 → 检查租户状态 → 检查角色权限 → 返回 APIKeyContext
```

## 租户状态检查

禁用的租户无法使用任何 API Key：

```python
# app/auth/api_key.py
if tenant.status != "active":
    raise HTTPException(
        status_code=403,
        detail={"code": "TENANT_DISABLED", "detail": f"Tenant is {tenant.status}"}
    )
```

## 限流机制

- 默认：120 次/分钟
- 可按 API Key 独立配置 `rate_limit_per_minute` 字段
- 支持内存限流器和 Redis 限流器

## 使用示例

```python
from app.auth.api_key import get_api_key_context, APIKeyContext

# 在路由中使用（通过依赖注入）
@router.get("/protected")
async def protected_route(context: APIKeyContext = Depends(get_api_key_context)):
    return {
        "tenant_id": context.tenant.id,
        "api_key_role": context.api_key.role
    }

# 角色权限检查（在 app/api/deps.py）
from app.api.deps import require_role

@router.post("/knowledge-bases")
async def create_kb(context: APIKeyContext = Depends(require_role("admin", "write"))):
    # 只有 admin 和 write 角色可以访问
    pass
```

## 管理员认证

Admin API 使用独立的 Token 认证：

```python
# app/api/deps.py
async def verify_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> str:
    """验证管理员 Token，通过 X-Admin-Token 请求头传递"""
```

配置：
```bash
# 环境变量
ADMIN_TOKEN=your-secure-admin-token
```

## 安全注意事项

- API Key 明文仅返回一次，无法恢复
- 生产环境应启用 HTTPS
- 定期轮换 Key（创建新 Key，删除旧 Key）
- 限流配置应根据实际负载调整
- Admin Token 应使用强随机字符串
