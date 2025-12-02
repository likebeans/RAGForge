# Auth 认证模块

API Key 认证和权限控制。

## 模块职责

- API Key 生成和验证
- 请求限流（Rate Limiting）
- 租户身份识别

## 核心文件

| 文件 | 说明 |
|------|------|
| `api_key.py` | API Key 认证逻辑、限流器 |

## API Key 设计

### 存储方式
- 明文 Key 仅在创建时返回一次
- 数据库存储 SHA256 哈希值
- 验证时对比哈希值

### Key 格式
```
sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 认证流程

```
请求 → Authorization Header → 提取 Bearer Token → SHA256 哈希 → 查询数据库 → 返回 Tenant
```

## 限流机制

- 默认：120 次/分钟
- 可按 API Key 独立配置 `rate_limit` 字段
- 使用内存计数器（生产环境建议替换为 Redis）

## 使用示例

```python
from app.auth.api_key import verify_api_key, get_tenant_from_key

# 验证 API Key 并获取租户
tenant = await get_tenant_from_key(db, api_key="sk-xxx")

# 在路由中使用（通过依赖注入）
@router.get("/protected")
async def protected_route(tenant: Tenant = Depends(get_current_tenant)):
    return {"tenant_id": tenant.id}
```

## 安全注意事项

- API Key 明文仅返回一次，无法恢复
- 生产环境应启用 HTTPS
- 定期轮换 Key（创建新 Key，删除旧 Key）
- 限流配置应根据实际负载调整
