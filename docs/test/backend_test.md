# yaoyan 后端测试文档

> 测试时间：2026-01-26  
> 后端地址：http://localhost:3002  
> API 文档：http://localhost:3002/docs

---

## 1. 环境准备

### 1.1 数据库

使用 RAGForge 的 PostgreSQL 实例，创建独立数据库：

```bash
# 创建 yaoyan 数据库
docker exec -it rag_kb_postgres psql -U kb -c "CREATE DATABASE yaoyan;"
```

**连接信息**：
- Host: `localhost:5435`
- User: `kb`
- Password: `kb`
- Database: `yaoyan`

### 1.2 启动后端

```bash
cd /home/admin1/yaoyan_AI/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 3002 --reload
```

### 1.3 数据库迁移

```bash
cd /home/admin1/yaoyan_AI/backend

# 生成迁移
uv run alembic revision --autogenerate -m "描述"

# 执行迁移
uv run alembic upgrade head
```

---

## 2. 初始数据

### 2.1 预置角色

| name | display_name | 说明 |
|------|-------------|------|
| finance | 财务人员 | 可访问财务相关文档 |
| tech | 技术人员 | 可访问技术相关文档 |
| hr | HR人员 | 可访问人事相关文档 |
| viewer | 普通用户 | 只能访问公开文档 |

### 2.2 预置部门

| name | display_name |
|------|-------------|
| dept_finance | 财务部 |
| dept_tech | 技术部 |
| dept_hr | 人事部 |
| dept_general | 综合部 |

### 2.3 管理员账号

| 用户名 | 密码 | clearance | is_admin |
|-------|------|-----------|----------|
| admin | admin123 | restricted | true |

---

## 3. API 测试

### 3.1 认证接口

#### 注册用户

```bash
curl -X POST http://localhost:3002/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test123",
    "display_name": "测试用户"
  }'
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "uuid",
    "username": "testuser",
    "display_name": "测试用户",
    "roles": [],
    "groups": [],
    "clearance": "public",
    "is_admin": false
  }
}
```

#### 登录

```bash
curl -X POST http://localhost:3002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "3ca06dde-e4eb-4943-83fa-61d2deab48c9",
    "username": "admin",
    "display_name": "管理员",
    "roles": [],
    "groups": [],
    "clearance": "restricted",
    "is_admin": true
  }
}
```

#### 获取当前用户

```bash
TOKEN="你的access_token"

curl http://localhost:3002/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**响应**：
```json
{
  "id": "3ca06dde-e4eb-4943-83fa-61d2deab48c9",
  "username": "admin",
  "display_name": "管理员",
  "email": null,
  "clearance": "restricted",
  "is_active": true,
  "is_admin": true,
  "roles": [],
  "groups": [],
  "created_at": "2026-01-26T08:45:55.652266Z",
  "updated_at": null
}
```

---

### 3.2 角色管理接口

#### 获取角色列表

```bash
curl http://localhost:3002/api/roles \
  -H "Authorization: Bearer $TOKEN"
```

**响应**：
```json
[
  {"id": "uuid", "name": "finance", "display_name": "财务人员", "description": "可访问财务相关文档", "created_at": "..."},
  {"id": "uuid", "name": "tech", "display_name": "技术人员", "description": "可访问技术相关文档", "created_at": "..."},
  {"id": "uuid", "name": "hr", "display_name": "HR人员", "description": "可访问人事相关文档", "created_at": "..."},
  {"id": "uuid", "name": "viewer", "display_name": "普通用户", "description": "只能访问公开文档", "created_at": "..."}
]
```

#### 创建角色（管理员）

```bash
curl -X POST http://localhost:3002/api/roles \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sales",
    "display_name": "销售人员",
    "description": "可访问销售相关文档"
  }'
```

---

### 3.3 部门管理接口

#### 获取部门列表

```bash
curl http://localhost:3002/api/groups \
  -H "Authorization: Bearer $TOKEN"
```

**响应**：
```json
[
  {"id": "uuid", "name": "dept_finance", "display_name": "财务部", "description": "财务部门", "parent_id": null, "created_at": "..."},
  {"id": "uuid", "name": "dept_tech", "display_name": "技术部", "description": "技术研发部门", "parent_id": null, "created_at": "..."},
  {"id": "uuid", "name": "dept_hr", "display_name": "人事部", "description": "人力资源部门", "parent_id": null, "created_at": "..."},
  {"id": "uuid", "name": "dept_general", "display_name": "综合部", "description": "综合管理部门", "parent_id": null, "created_at": "..."}
]
```

#### 创建部门（管理员）

```bash
curl -X POST http://localhost:3002/api/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dept_sales",
    "display_name": "销售部",
    "description": "销售部门"
  }'
```

---

### 3.4 用户管理接口

#### 获取用户列表（管理员）

```bash
curl http://localhost:3002/api/users \
  -H "Authorization: Bearer $TOKEN"
```

#### 创建用户（管理员）

```bash
curl -X POST http://localhost:3002/api/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "password": "zhang123",
    "display_name": "张三",
    "clearance": "restricted",
    "role_ids": ["<finance_role_id>"],
    "group_ids": ["<dept_finance_id>"]
  }'
```

#### 设置用户角色（管理员）

```bash
curl -X PUT http://localhost:3002/api/users/{user_id}/roles \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role_ids": ["<role_id_1>", "<role_id_2>"]
  }'
```

#### 设置用户部门（管理员）

```bash
curl -X PUT http://localhost:3002/api/users/{user_id}/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_ids": ["<group_id_1>"]
  }'
```

---

### 3.5 RAGForge 代理接口

#### 获取知识库列表

```bash
curl http://localhost:3002/api/ragforge/knowledge-bases \
  -H "Authorization: Bearer $TOKEN"
```

**响应**（代理自 RAGForge）：
```json
{
  "items": [
    {"id": "7bc7b72c-051a-416b-b5c0-7ca131693118", "name": "ACL完整测试", ...},
    {"id": "6ce20955-07cf-4f3e-bb9c-4b86858421b8", "name": "ACL测试v6-带embedding配置", ...}
  ],
  "total": 12
}
```

#### 检索（自动注入 identity）

```bash
curl -X POST http://localhost:3002/api/ragforge/retrieve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "公司简介",
    "knowledge_base_ids": ["7bc7b72c-051a-416b-b5c0-7ca131693118"],
    "top_k": 5
  }'
```

**响应**：
```json
{
  "results": [
    {
      "content": "这是公开信息，包含公司简介和产品介绍。",
      "score": 0.85,
      "metadata": {
        "title": "公开文档",
        "sensitivity_level": "public"
      }
    },
    {
      "content": "技术部门核心算法和架构设计。",
      "score": 0.72,
      "metadata": {
        "title": "技术机密",
        "sensitivity_level": "restricted"
      }
    },
    {
      "content": "财务部门机密预算报告和薪资方案。",
      "score": 0.68,
      "metadata": {
        "title": "财务机密",
        "sensitivity_level": "restricted"
      }
    }
  ]
}
```

> **注意**：admin 用户 clearance=restricted，所以能看到所有文档。普通用户只能看到 public 文档。

#### RAG 问答

```bash
curl -X POST http://localhost:3002/api/ragforge/rag \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "请介绍一下公司",
    "knowledge_base_ids": ["7bc7b72c-051a-416b-b5c0-7ca131693118"],
    "top_k": 5
  }'
```

---

## 4. 完整测试脚本

```bash
#!/bin/bash

BASE_URL="http://localhost:3002"

echo "=========================================="
echo "yaoyan 后端 API 测试"
echo "=========================================="

# 1. 登录获取 Token
echo ""
echo "=== 1. 登录 ==="
LOGIN_RESULT=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo $LOGIN_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
echo "Token: ${TOKEN:0:30}..."

# 2. 获取当前用户
echo ""
echo "=== 2. 获取当前用户 ==="
curl -s "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
u = json.load(sys.stdin)
print(f'用户: {u[\"username\"]} ({u[\"display_name\"]})')
print(f'权限: clearance={u[\"clearance\"]}, is_admin={u[\"is_admin\"]}')
"

# 3. 获取角色列表
echo ""
echo "=== 3. 角色列表 ==="
curl -s "$BASE_URL/api/roles" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
for r in json.load(sys.stdin):
    print(f'  {r[\"name\"]}: {r[\"display_name\"]}')
"

# 4. 获取部门列表
echo ""
echo "=== 4. 部门列表 ==="
curl -s "$BASE_URL/api/groups" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
for g in json.load(sys.stdin):
    print(f'  {g[\"name\"]}: {g[\"display_name\"]}')
"

# 5. RAGForge 代理 - 获取知识库
echo ""
echo "=== 5. 知识库列表（RAGForge 代理）==="
curl -s "$BASE_URL/api/ragforge/knowledge-bases" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
data = json.load(sys.stdin)
print(f'知识库数量: {len(data.get(\"items\",[]))}')
for kb in data.get('items',[])[:3]:
    print(f'  - {kb[\"name\"]}: {kb[\"id\"][:8]}...')
"

# 6. RAGForge 代理 - 检索
echo ""
echo "=== 6. 检索测试（RAGForge 代理）==="
curl -s -X POST "$BASE_URL/api/ragforge/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"公司简介","knowledge_base_ids":["7bc7b72c-051a-416b-b5c0-7ca131693118"],"top_k":3}' | python3 -c "
import sys,json
data = json.load(sys.stdin)
print(f'检索结果: {len(data.get(\"results\",[]))} 条')
for r in data.get('results',[]):
    title = r.get('metadata',{}).get('title','N/A')
    sens = r.get('metadata',{}).get('sensitivity_level','N/A')
    print(f'  - {title} [{sens}]')
"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
```

---

## 5. 测试结果汇总

| 测试项 | 预期结果 | 实际结果 | 状态 |
|--------|---------|---------|------|
| 健康检查 GET / | 返回 status=running | ✅ 正常 | ✅ |
| 用户注册 POST /api/auth/register | 返回 Token | ✅ 正常 | ✅ |
| 用户登录 POST /api/auth/login | 返回 Token | ✅ 正常 | ✅ |
| 获取当前用户 GET /api/auth/me | 返回用户信息 | ✅ 正常 | ✅ |
| 获取角色列表 GET /api/roles | 返回 4 个角色 | ✅ 正常 | ✅ |
| 获取部门列表 GET /api/groups | 返回 4 个部门 | ✅ 正常 | ✅ |
| RAGForge 代理 - 知识库列表 | 返回知识库 | ✅ 返回 12 个 | ✅ |
| RAGForge 代理 - 检索 | 返回检索结果 | ✅ 返回 3 条 | ✅ |
| API Key 自动创建 | 首次代理时自动创建 | ✅ 已创建 | ✅ |

---

## 6. API Key 映射机制

### 6.1 自动创建流程

1. 用户通过 yaoyan 后端调用 RAGForge 代理接口
2. 后端检查 `api_key_mappings` 表是否有该用户的有效 API Key
3. 如果没有，自动调用 RAGForge `/v1/api-keys` 创建新 Key
4. 创建时注入用户的 identity（roles, groups, clearance）
5. 保存映射到数据库

### 6.2 Identity 结构

```json
{
  "user_id": "3ca06dde-e4eb-4943-83fa-61d2deab48c9",
  "roles": ["finance"],
  "groups": ["dept_finance"],
  "clearance": "restricted"
}
```

### 6.3 验证 API Key 映射

```bash
docker exec rag_kb_postgres psql -U kb -d yaoyan -c "
SELECT 
  u.username,
  m.ragforge_key_id,
  m.is_valid,
  m.identity_snapshot
FROM api_key_mappings m
JOIN users u ON u.id = m.user_id;
"
```

**输出**：
```
 username |           ragforge_key_id            | is_valid |                  identity_snapshot
----------+--------------------------------------+----------+-----------------------------------------------------
 admin    | 65f329d4-cf41-48eb-a011-b8a96bf12467 | t        | {"user_id": "...", "roles": [], "groups": [], "clearance": "restricted"}
```

---

## 7. 注意事项

### 7.1 角色变更同步

当用户角色或部门变更时，需要使旧的 API Key 失效：

```sql
UPDATE api_key_mappings 
SET is_valid = false 
WHERE user_id = '<user_id>';
```

下次用户调用代理接口时，会自动创建新的 API Key。

### 7.2 数据库连接

yaoyan 后端使用的数据库连接：
```
DATABASE_URL=postgresql+asyncpg://kb:kb@localhost:5435/yaoyan
```

### 7.3 RAGForge 配置

```
RAGFORGE_BASE_URL=http://192.168.168.105:8020
RAGFORGE_ADMIN_KEY=kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ
```

---

## 8. 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── api/
│   │   ├── deps.py             # 依赖注入（认证）
│   │   └── routes/
│   │       ├── auth.py         # 认证接口
│   │       ├── users.py        # 用户管理
│   │       ├── roles.py        # 角色管理
│   │       ├── groups.py       # 部门管理
│   │       └── ragforge.py     # RAGForge 代理
│   ├── auth/
│   │   ├── jwt.py              # JWT 工具
│   │   └── password.py         # 密码加密
│   ├── db/
│   │   ├── base.py             # SQLAlchemy Base
│   │   └── session.py          # 数据库会话
│   ├── models/
│   │   ├── user.py             # 用户模型
│   │   ├── role.py             # 角色模型
│   │   ├── group.py            # 部门模型
│   │   └── api_key_mapping.py  # API Key 映射
│   ├── schemas/                # Pydantic 模型
│   └── services/
│       ├── auth_service.py     # 认证服务
│       ├── user_service.py     # 用户服务
│       └── ragforge_service.py # RAGForge 集成
├── alembic/                    # 数据库迁移
├── .env                        # 环境变量
└── alembic.ini
```

---

## 文档版本

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0 | 2026-01-26 | 初始版本，后端开发完成测试 |
