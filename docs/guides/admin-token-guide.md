# Admin Token 迁移指南

## 概述

Admin Token 已从环境变量明文存储升级为数据库哈希存储，提高安全性。

## 新功能

1. **哈希存储**：Token 使用 SHA256 哈希存储，无法恢复明文
2. **多 Token 支持**：可创建多个管理员 Token
3. **过期时间**：支持设置 Token 过期时间
4. **撤销机制**：可随时撤销 Token
5. **使用追踪**：记录 Token 最后使用时间

## 数据库迁移

### 创建 admin_tokens 表

```sql
CREATE TABLE admin_tokens (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    prefix VARCHAR(12) NOT NULL,
    hashed_token VARCHAR(128) NOT NULL UNIQUE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_admin_tokens_prefix ON admin_tokens(prefix);
CREATE INDEX ix_admin_tokens_revoked ON admin_tokens(revoked);
```

### 使用 Alembic 迁移

```bash
# 生成迁移文件
uv run alembic revision --autogenerate -m "Add AdminToken model"

# 应用迁移
uv run alembic upgrade head
```

## 使用方式

### 创建管理员 Token

```bash
curl -X POST http://localhost:8020/admin/tokens \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "主管理员",
    "description": "系统主管理员 Token",
    "expires_at": null
  }'
```

响应：
```json
{
  "id": "xxx",
  "name": "主管理员",
  "prefix": "admin_abc123",
  "token": "admin_abc123...full_token...",  // 仅返回一次，请保存
  "created_at": "2026-01-15T00:00:00Z"
}
```

### 列出所有 Token

```bash
curl http://localhost:8020/admin/tokens \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

### 撤销 Token

```bash
curl -X POST http://localhost:8020/admin/tokens/{token_id}/revoke \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

## 向后兼容

系统支持向后兼容，优先级：

1. **数据库 Token**：优先使用数据库中的 Token
2. **环境变量**：如果数据库中没有 Token，回退到环境变量 `ADMIN_TOKEN`

### 迁移步骤

1. **创建数据库 Token**：使用现有环境变量创建第一个数据库 Token
2. **测试验证**：确认新 Token 可正常使用
3. **更新配置**：将应用迁移到新 Token
4. **移除环境变量**：（可选）移除 `ADMIN_TOKEN` 环境变量

## 安全建议

1. **立即迁移**：尽快从环境变量迁移到数据库存储
2. **定期轮换**：建议每 3-6 个月轮换 Token
3. **最小权限**：为不同团队创建独立 Token
4. **监控使用**：定期检查 Token 使用情况
5. **及时撤销**：发现泄漏立即撤销 Token

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/tokens` | 创建 Token |
| GET | `/admin/tokens` | 列出 Token |
| GET | `/admin/tokens/{id}` | 获取详情 |
| POST | `/admin/tokens/{id}/revoke` | 撤销 Token |
| DELETE | `/admin/tokens/{id}` | 删除 Token |

## 故障排除

### 问题：Token 验证失败

**解决**：
1. 检查 Token 是否已过期
2. 检查 Token 是否已撤销
3. 检查数据库连接是否正常

### 问题：无法创建 Token

**解决**：
1. 确认已运行数据库迁移
2. 检查当前 Token 是否有效
3. 查看应用日志

## 相关文件

- `app/models/admin_token.py` - ORM 模型
- `app/auth/admin_token.py` - 认证逻辑
- `app/api/routes/admin_tokens.py` - API 路由
- `app/schemas/admin_token.py` - Pydantic schemas
