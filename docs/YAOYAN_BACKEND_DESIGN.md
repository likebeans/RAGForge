# yaoyan 后端开发设计文档

> 版本：v1.0  
> 日期：2026-01-26  
> 作者：Cascade AI  

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [技术栈](#3-技术栈)
4. [项目结构](#4-项目结构)
5. [数据库设计](#5-数据库设计)
6. [API 设计](#6-api-设计)
7. [核心流程](#7-核心流程)
8. [与 RAGForge 集成](#8-与-ragforge-集成)
9. [安全设计](#9-安全设计)
10. [开发计划](#10-开发计划)
11. [部署方案](#11-部署方案)

---

## 1. 项目概述

### 1.1 背景

yaoyan 是一个基于 RAGForge 的 AI 知识问答前端应用。当前前端直接调用 RAGForge API，但缺少以下能力：

- **用户认证**：无登录系统，无法区分用户身份
- **用户管理**：无法管理用户、角色、部门
- **权限映射**：无法将用户身份自动映射到 RAGForge 的 ACL 系统
- **数据持久化**：用户/角色数据存储在 localStorage，不可靠

### 1.2 目标

构建 yaoyan 后端服务，实现：

| 目标 | 描述 |
|------|------|
| 用户认证 | JWT Token 登录，会话管理 |
| 用户管理 | 用户、角色、部门的 CRUD |
| 权限桥接 | 自动为用户创建 RAGForge API Key，注入 identity |
| API 代理 | 代理 RAGForge 请求，自动附加用户权限 |

### 1.3 核心价值

```
用户登录 → yaoyan 后端验证身份 → 获取用户角色/部门 → 
调用 RAGForge 时自动注入 identity → RAGForge ACL 过滤生效
```

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    yaoyan 前端 (React)                          │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   登录页    │  │  AI 对话    │  │ 用户管理    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   yaoyan 后端 (FastAPI)                         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  认证模块   │  │ RAGForge   │  │  用户管理   │              │
│  │  (JWT)     │  │   代理      │  │   CRUD     │              │
│  └─────────────┘  └──────┬──────┘  └─────────────┘             │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────┐             │
│  │              RAGForge 服务层                   │             │
│  │  - 为用户创建/管理 API Key                     │             │
│  │  - 代理请求并自动注入 identity                 │             │
│  └───────────────────────────────────────────────┘             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAGForge 服务                                │
│                    http://192.168.168.105:8020                  │
│                                                                 │
│  - 知识库管理                                                   │
│  - 文档检索（带 ACL 过滤）                                      │
│  - RAG 问答                                                     │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL                                   │
│                                                                 │
│  yaoyan 数据库          │          RAGForge 数据库              │
│  ├── users             │          ├── tenants                  │
│  ├── roles             │          ├── api_keys                 │
│  ├── groups            │          ├── knowledge_bases          │
│  ├── user_roles        │          ├── documents                │
│  ├── user_groups       │          └── chunks                   │
│  └── api_key_mappings  │                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 请求流程

```
1. 用户登录
   前端 → POST /api/auth/login → 后端验证 → 返回 JWT Token

2. AI 对话（带权限）
   前端 → POST /api/ragforge/rag (Bearer JWT)
        → 后端解析 JWT，获取用户信息
        → 查询用户的角色、部门
        → 获取/创建该用户的 RAGForge API Key
        → 代理请求到 RAGForge（Bearer 用户专属 API Key）
        → RAGForge 根据 API Key 的 identity 进行 ACL 过滤
        → 返回结果

3. 用户管理
   前端 → GET/POST/PUT/DELETE /api/users (Bearer JWT + Admin)
        → 后端验证管理员权限
        → 执行 CRUD 操作
        → 同步更新 RAGForge API Key 的 identity（如果角色变更）
```

---

## 3. 技术栈

### 3.1 核心框架（参考 RAGForge）

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Web 框架 | **FastAPI** | 与 RAGForge 一致，高性能异步框架 |
| ORM | **SQLAlchemy 2.0** | 异步 ORM，与 RAGForge 一致 |
| 数据库迁移 | **Alembic** | 与 RAGForge 一致 |
| 数据库驱动 | **asyncpg** | PostgreSQL 异步驱动 |
| 数据验证 | **Pydantic v2** | 请求/响应模型验证 |
| HTTP 客户端 | **httpx** | 异步 HTTP 客户端，调用 RAGForge |
| 认证 | **python-jose** | JWT Token 生成与验证 |
| 密码加密 | **passlib[bcrypt]** | 密码哈希 |

### 3.2 与 RAGForge 的技术一致性

```python
# RAGForge 使用的模式，yaoyan 后端保持一致：

# 1. 配置管理
from app.config import get_settings
settings = get_settings()

# 2. 数据库会话
from app.db.session import get_db
async def get_users(db: AsyncSession = Depends(get_db)):
    ...

# 3. 模型定义
from app.db.base import Base
class User(TimestampMixin, Base):
    __tablename__ = "users"
    ...

# 4. Pydantic Schema
class UserCreate(BaseModel):
    username: str
    password: str
    ...
```

---

## 4. 项目结构

```
yaoyan-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理（环境变量）
│   ├── exceptions.py           # 自定义异常
│   │
│   ├── api/                    # API 路由层
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入（认证、数据库）
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py         # 认证接口（登录、注册）
│   │       ├── users.py        # 用户管理
│   │       ├── roles.py        # 角色管理
│   │       ├── groups.py       # 部门管理
│   │       └── ragforge.py     # RAGForge 代理接口
│   │
│   ├── auth/                   # 认证模块
│   │   ├── __init__.py
│   │   ├── jwt.py              # JWT 工具函数
│   │   └── password.py         # 密码加密工具
│   │
│   ├── db/                     # 数据库配置
│   │   ├── __init__.py
│   │   ├── base.py             # SQLAlchemy Base
│   │   └── session.py          # 数据库会话管理
│   │
│   ├── models/                 # ORM 模型
│   │   ├── __init__.py
│   │   ├── mixins.py           # 通用 Mixin（时间戳等）
│   │   ├── user.py             # 用户模型
│   │   ├── role.py             # 角色模型
│   │   ├── group.py            # 部门模型
│   │   └── api_key_mapping.py  # API Key 映射表
│   │
│   ├── schemas/                # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证相关 Schema
│   │   ├── user.py             # 用户相关 Schema
│   │   ├── role.py             # 角色相关 Schema
│   │   ├── group.py            # 部门相关 Schema
│   │   └── ragforge.py         # RAGForge 代理 Schema
│   │
│   └── services/               # 业务逻辑层
│       ├── __init__.py
│       ├── auth_service.py     # 认证服务
│       ├── user_service.py     # 用户服务
│       └── ragforge_service.py # RAGForge 集成服务
│
├── alembic/                    # 数据库迁移
│   ├── versions/
│   └── env.py
│
├── tests/                      # 测试
│   ├── __init__.py
│   ├── conftest.py
│   └── test_auth.py
│
├── .env                        # 环境变量
├── .env.example                # 环境变量模板
├── alembic.ini                 # Alembic 配置
├── requirements.txt            # 依赖
├── pyproject.toml              # 项目配置
└── README.md
```

---

## 5. 数据库设计

### 5.1 ER 图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    users    │       │    roles    │       │   groups    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ username    │       │ name        │       │ name        │
│ password_hash│      │ description │       │ description │
│ email       │       │ permissions │       │ parent_id   │
│ clearance   │       │ created_at  │       │ created_at  │
│ is_active   │       │ updated_at  │       │ updated_at  │
│ created_at  │       └──────┬──────┘       └──────┬──────┘
│ updated_at  │              │                     │
└──────┬──────┘              │                     │
       │                     │                     │
       │    ┌────────────────┴─────────────────┐   │
       │    │                                  │   │
       ▼    ▼                                  ▼   ▼
┌─────────────────┐                    ┌─────────────────┐
│   user_roles    │                    │   user_groups   │
├─────────────────┤                    ├─────────────────┤
│ user_id (FK)    │                    │ user_id (FK)    │
│ role_id (FK)    │                    │ group_id (FK)   │
│ (PK: composite) │                    │ (PK: composite) │
└─────────────────┘                    └─────────────────┘

┌─────────────────────┐
│  api_key_mappings   │      yaoyan 用户 → RAGForge API Key 映射
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ ragforge_key_id     │      RAGForge 返回的 API Key ID
│ ragforge_api_key    │      完整 API Key（加密存储）
│ identity_snapshot   │      创建时的 identity 快照（JSON）
│ created_at          │
│ updated_at          │
└─────────────────────┘
```

### 5.2 表结构详细设计

#### users 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 用户唯一标识 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名（登录用） |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| email | VARCHAR(100) | UNIQUE | 邮箱（可选） |
| display_name | VARCHAR(100) | | 显示名称 |
| clearance | VARCHAR(20) | DEFAULT 'public' | 敏感度访问级别 |
| is_active | BOOLEAN | DEFAULT true | 账号是否启用 |
| is_admin | BOOLEAN | DEFAULT false | 是否为管理员 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

**clearance 取值**：
- `public`：只能访问公开文档
- `restricted`：可以访问受限文档（需 ACL 匹配）

#### roles 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 角色唯一标识 |
| name | VARCHAR(50) | UNIQUE, NOT NULL | 角色名称（如 finance, tech） |
| display_name | VARCHAR(100) | | 显示名称（如 财务人员） |
| description | TEXT | | 角色描述 |
| permissions | JSON | DEFAULT '[]' | 权限列表（预留） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

#### groups 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 部门唯一标识 |
| name | VARCHAR(50) | UNIQUE, NOT NULL | 部门名称（如 dept_finance） |
| display_name | VARCHAR(100) | | 显示名称（如 财务部） |
| description | TEXT | | 部门描述 |
| parent_id | UUID | FK(groups.id) | 父部门（支持层级） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

#### api_key_mappings 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 映射唯一标识 |
| user_id | UUID | FK(users.id), UNIQUE | 关联用户（一对一） |
| ragforge_key_id | VARCHAR(100) | | RAGForge API Key ID |
| ragforge_api_key | TEXT | | 完整 API Key（加密） |
| identity_snapshot | JSON | | 创建时的 identity |
| is_valid | BOOLEAN | DEFAULT true | 是否有效 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 5.3 初始数据

```sql
-- 预置角色
INSERT INTO roles (id, name, display_name, description) VALUES
  (gen_random_uuid(), 'admin', '管理员', '系统管理员，拥有所有权限'),
  (gen_random_uuid(), 'finance', '财务人员', '可访问财务相关文档'),
  (gen_random_uuid(), 'tech', '技术人员', '可访问技术相关文档'),
  (gen_random_uuid(), 'hr', 'HR人员', '可访问人事相关文档'),
  (gen_random_uuid(), 'viewer', '普通用户', '只能访问公开文档');

-- 预置部门
INSERT INTO groups (id, name, display_name, description) VALUES
  (gen_random_uuid(), 'dept_finance', '财务部', '财务部门'),
  (gen_random_uuid(), 'dept_tech', '技术部', '技术研发部门'),
  (gen_random_uuid(), 'dept_hr', '人事部', '人力资源部门'),
  (gen_random_uuid(), 'dept_general', '综合部', '综合管理部门');

-- 预置管理员账号
INSERT INTO users (id, username, password_hash, clearance, is_admin) VALUES
  (gen_random_uuid(), 'admin', '$2b$12$...hashed...', 'restricted', true);
```

---

## 6. API 设计

### 6.1 API 概览

| 分类 | 端点 | 方法 | 说明 |
|------|------|------|------|
| **认证** | `/api/auth/login` | POST | 用户登录 |
| | `/api/auth/register` | POST | 用户注册 |
| | `/api/auth/me` | GET | 获取当前用户信息 |
| | `/api/auth/refresh` | POST | 刷新 Token |
| **用户** | `/api/users` | GET | 获取用户列表 |
| | `/api/users` | POST | 创建用户 |
| | `/api/users/{id}` | GET | 获取用户详情 |
| | `/api/users/{id}` | PUT | 更新用户 |
| | `/api/users/{id}` | DELETE | 删除用户 |
| | `/api/users/{id}/roles` | PUT | 设置用户角色 |
| | `/api/users/{id}/groups` | PUT | 设置用户部门 |
| **角色** | `/api/roles` | GET | 获取角色列表 |
| | `/api/roles` | POST | 创建角色 |
| | `/api/roles/{id}` | PUT | 更新角色 |
| | `/api/roles/{id}` | DELETE | 删除角色 |
| **部门** | `/api/groups` | GET | 获取部门列表 |
| | `/api/groups` | POST | 创建部门 |
| | `/api/groups/{id}` | PUT | 更新部门 |
| | `/api/groups/{id}` | DELETE | 删除部门 |
| **RAGForge 代理** | `/api/ragforge/knowledge-bases` | GET | 获取知识库列表 |
| | `/api/ragforge/retrieve` | POST | 检索（自动注入权限） |
| | `/api/ragforge/rag` | POST | RAG 问答（自动注入权限） |
| | `/api/ragforge/rag/stream` | POST | RAG 流式问答 |

### 6.2 认证 API 详细设计

#### POST /api/auth/login

**请求**：
```json
{
  "username": "zhangsan",
  "password": "password123"
}
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "zhangsan",
    "display_name": "张三",
    "roles": ["finance"],
    "groups": ["dept_finance"],
    "clearance": "restricted",
    "is_admin": false
  }
}
```

#### GET /api/auth/me

**请求头**：
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**响应**：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "zhangsan",
  "display_name": "张三",
  "email": "zhangsan@example.com",
  "roles": [
    {"id": "...", "name": "finance", "display_name": "财务人员"}
  ],
  "groups": [
    {"id": "...", "name": "dept_finance", "display_name": "财务部"}
  ],
  "clearance": "restricted",
  "is_admin": false,
  "created_at": "2026-01-26T10:00:00Z"
}
```

### 6.3 用户管理 API 详细设计

#### POST /api/users

**请求**（需管理员权限）：
```json
{
  "username": "lisi",
  "password": "password123",
  "display_name": "李四",
  "email": "lisi@example.com",
  "clearance": "restricted",
  "role_ids": ["role-uuid-1", "role-uuid-2"],
  "group_ids": ["group-uuid-1"]
}
```

**响应**：
```json
{
  "id": "new-user-uuid",
  "username": "lisi",
  "display_name": "李四",
  "roles": ["finance", "viewer"],
  "groups": ["dept_finance"],
  "clearance": "restricted",
  "created_at": "2026-01-26T10:00:00Z"
}
```

#### PUT /api/users/{id}/roles

**请求**：
```json
{
  "role_ids": ["role-uuid-1", "role-uuid-2"]
}
```

**响应**：
```json
{
  "message": "Roles updated successfully",
  "roles": ["finance", "tech"],
  "ragforge_key_updated": true
}
```

> **注意**：更新用户角色时，需要同步更新该用户在 RAGForge 的 API Key identity。

### 6.4 RAGForge 代理 API 详细设计

#### POST /api/ragforge/retrieve

**请求**：
```json
{
  "query": "公司财务预算是多少？",
  "knowledge_base_ids": ["kb-uuid-1"],
  "top_k": 5
}
```

**内部处理**：
```
1. 从 JWT 获取 user_id
2. 查询用户的 roles、groups、clearance
3. 获取或创建用户的 RAGForge API Key（带 identity）
4. 使用该 API Key 调用 RAGForge /v1/retrieve
5. RAGForge 根据 identity 进行 ACL 过滤
6. 返回过滤后的结果
```

**响应**（透传 RAGForge 响应）：
```json
{
  "results": [
    {
      "content": "2026年公司预算为1000万...",
      "score": 0.95,
      "metadata": {
        "title": "财务机密报告",
        "sensitivity_level": "restricted"
      }
    }
  ]
}
```

#### POST /api/ragforge/rag

**请求**：
```json
{
  "query": "请总结一下公司的技术架构",
  "knowledge_base_ids": ["kb-uuid-1"],
  "stream": false
}
```

**响应**：
```json
{
  "answer": "根据检索到的文档，公司技术架构主要包括...",
  "sources": [
    {
      "title": "技术架构文档",
      "content": "..."
    }
  ]
}
```

---

## 7. 核心流程

### 7.1 用户登录流程

```
┌──────┐     ┌──────────────┐     ┌──────────────┐
│ 前端 │     │ yaoyan 后端  │     │  PostgreSQL  │
└──┬───┘     └──────┬───────┘     └──────┬───────┘
   │                │                    │
   │ POST /login    │                    │
   │ {username,pwd} │                    │
   │───────────────>│                    │
   │                │                    │
   │                │ SELECT * FROM users│
   │                │ WHERE username=?   │
   │                │───────────────────>│
   │                │                    │
   │                │    user record     │
   │                │<───────────────────│
   │                │                    │
   │                │ verify password    │
   │                │ (bcrypt)           │
   │                │                    │
   │                │ generate JWT       │
   │                │ {user_id, exp}     │
   │                │                    │
   │  {token, user} │                    │
   │<───────────────│                    │
   │                │                    │
```

### 7.2 RAGForge 代理流程（核心）

```
┌──────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 前端 │     │ yaoyan 后端  │     │  PostgreSQL  │     │  RAGForge    │
└──┬───┘     └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
   │                │                    │                    │
   │ POST /ragforge/│                    │                    │
   │ retrieve       │                    │                    │
   │ Bearer: JWT    │                    │                    │
   │───────────────>│                    │                    │
   │                │                    │                    │
   │                │ 1. 验证 JWT        │                    │
   │                │    提取 user_id    │                    │
   │                │                    │                    │
   │                │ 2. 查询用户信息    │                    │
   │                │───────────────────>│                    │
   │                │                    │                    │
   │                │ user + roles +     │                    │
   │                │ groups             │                    │
   │                │<───────────────────│                    │
   │                │                    │                    │
   │                │ 3. 查询 API Key    │                    │
   │                │    映射表          │                    │
   │                │───────────────────>│                    │
   │                │                    │                    │
   │                │ api_key_mapping    │                    │
   │                │<───────────────────│                    │
   │                │                    │                    │
   │                │ 4. 如果没有 API Key│                    │
   │                │    或 identity 变更│                    │
   │                │                    │ POST /v1/api-keys  │
   │                │                    │ identity: {        │
   │                │                    │   user_id,         │
   │                │                    │   roles,           │
   │                │                    │   groups,          │
   │                │                    │   clearance        │
   │                │                    │ }                  │
   │                │────────────────────┼───────────────────>│
   │                │                    │                    │
   │                │                    │   new API Key      │
   │                │<───────────────────┼────────────────────│
   │                │                    │                    │
   │                │ 5. 保存 API Key    │                    │
   │                │───────────────────>│                    │
   │                │                    │                    │
   │                │ 6. 代理检索请求    │                    │
   │                │    Bearer: 用户的  │ POST /v1/retrieve  │
   │                │    RAGForge Key    │                    │
   │                │────────────────────┼───────────────────>│
   │                │                    │                    │
   │                │                    │ RAGForge 根据      │
   │                │                    │ identity 进行      │
   │                │                    │ ACL 过滤           │
   │                │                    │                    │
   │                │   filtered results │                    │
   │                │<───────────────────┼────────────────────│
   │                │                    │                    │
   │  results       │                    │                    │
   │<───────────────│                    │                    │
```

### 7.3 用户角色变更同步流程

```
当用户角色/部门变更时，需要同步更新 RAGForge API Key：

1. 管理员更新用户角色
   PUT /api/users/{id}/roles

2. yaoyan 后端更新数据库

3. 检查该用户是否有 RAGForge API Key
   - 如果有，标记为无效（is_valid = false）
   - 下次该用户请求时，会创建新的 API Key

或者：

3. 直接调用 RAGForge 更新 API Key
   - 如果 RAGForge 支持更新 identity（待确认）
   - 或者删除旧 Key，创建新 Key
```

---

## 8. 与 RAGForge 集成

### 8.1 RAGForge API 调用

yaoyan 后端需要调用以下 RAGForge API：

| API | 用途 |
|-----|------|
| `POST /v1/api-keys` | 为用户创建专属 API Key |
| `DELETE /v1/api-keys/{id}` | 删除失效的 API Key |
| `POST /v1/retrieve` | 代理检索请求 |
| `POST /v1/rag` | 代理 RAG 问答 |
| `GET /v1/knowledge-bases` | 获取知识库列表 |

### 8.2 API Key Identity 结构

创建用户 API Key 时，identity 结构如下：

```json
{
  "user_id": "yaoyan-user-uuid",
  "roles": ["finance", "viewer"],
  "groups": ["dept_finance"],
  "clearance": "restricted"
}
```

**字段说明**：

| 字段 | 说明 | 来源 |
|------|------|------|
| user_id | 用户 ID | yaoyan users.id |
| roles | 角色名称列表 | yaoyan user_roles → roles.name |
| groups | 部门名称列表 | yaoyan user_groups → groups.name |
| clearance | 敏感度级别 | yaoyan users.clearance |

### 8.3 RAGForge 服务类设计

```
RagForgeService 职责：

1. 管理用户 API Key
   - get_or_create_user_api_key(user_id) → api_key
   - invalidate_user_api_key(user_id)
   - refresh_user_api_key(user_id) → api_key

2. 代理请求
   - retrieve(api_key, request) → response
   - rag(api_key, request) → response
   - rag_stream(api_key, request) → async generator

3. 知识库管理（可选，管理员）
   - list_knowledge_bases() → list
   - get_knowledge_base(kb_id) → kb
```

---

## 9. 安全设计

### 9.1 认证安全

| 措施 | 说明 |
|------|------|
| JWT 签名 | 使用 HS256 或 RS256 算法 |
| Token 有效期 | 默认 7 天，可配置 |
| 密码存储 | bcrypt 哈希，成本因子 12 |
| 密码复杂度 | 最少 8 位，包含字母和数字 |

### 9.2 API Key 安全

| 措施 | 说明 |
|------|------|
| 加密存储 | RAGForge API Key 使用 AES 加密存储 |
| 单一映射 | 每个用户只有一个有效的 RAGForge API Key |
| 自动失效 | 用户角色变更时自动失效旧 Key |

### 9.3 权限控制

| 资源 | 普通用户 | 管理员 |
|------|---------|--------|
| 查看自己信息 | ✅ | ✅ |
| 修改自己密码 | ✅ | ✅ |
| 查看用户列表 | ❌ | ✅ |
| 创建/修改/删除用户 | ❌ | ✅ |
| 管理角色/部门 | ❌ | ✅ |
| 使用 RAGForge 代理 | ✅ | ✅ |

### 9.4 请求限流

| 端点 | 限制 |
|------|------|
| `/api/auth/login` | 10 次/分钟/IP |
| `/api/ragforge/*` | 60 次/分钟/用户 |
| 其他 | 100 次/分钟/用户 |

---

## 10. 开发计划

### 10.1 阶段划分

| 阶段 | 内容 | 预计时间 | 优先级 |
|------|------|---------|--------|
| **P0** | 项目初始化、数据库、基础框架 | 2 小时 | 高 |
| **P1** | 用户认证（登录/注册/JWT） | 2 小时 | 高 |
| **P2** | 用户管理 CRUD | 2 小时 | 高 |
| **P3** | 角色/部门管理 | 1.5 小时 | 中 |
| **P4** | RAGForge 代理（核心） | 3 小时 | 高 |
| **P5** | 前端集成 | 2 小时 | 中 |
| **P6** | 测试、文档 | 1.5 小时 | 中 |

**总计：约 14 小时**

### 10.2 详细任务清单

#### P0: 项目初始化（2 小时）

- [x] 创建项目目录结构
- [x] 初始化 pyproject.toml 和 requirements.txt
- [x] 配置 FastAPI 应用入口
- [x] 配置数据库连接（参考 RAGForge）
- [x] 创建 Alembic 迁移环境
- [x] 创建数据库表（初始迁移）
- [x] 配置 CORS、异常处理

#### P1: 用户认证（2 小时）

- [x] 实现 JWT 工具函数
- [x] 实现密码加密工具
- [x] 实现 POST /api/auth/login
- [x] 实现 POST /api/auth/register
- [x] 实现 GET /api/auth/me
- [x] 实现认证依赖注入

#### P2: 用户管理（2 小时）

- [x] 实现 UserService
- [x] 实现 GET /api/users
- [x] 实现 POST /api/users
- [x] 实现 GET /api/users/{id}
- [x] 实现 PUT /api/users/{id}
- [x] 实现 DELETE /api/users/{id}
- [x] 实现 PUT /api/users/{id}/roles
- [x] 实现 PUT /api/users/{id}/groups

#### P3: 角色/部门管理（1.5 小时）

- [x] 实现角色 CRUD
- [x] 实现部门 CRUD
- [x] 添加初始数据

#### P4: RAGForge 代理（3 小时）

- [x] 实现 RagForgeService
- [x] 实现 API Key 创建/管理
- [x] 实现 POST /api/ragforge/retrieve
- [x] 实现 POST /api/ragforge/rag
- [x] 实现 POST /api/ragforge/rag/stream
- [x] 实现角色变更时的 Key 同步
- [x] 实现 API Key 加密存储

#### P5: 前端集成（2 小时）

- [x] 更新前端 API 客户端
- [x] 添加登录页面
- [x] 更新用户管理页面
- [x] 更新 Chat 页面调用方式
- [x] 测试端到端流程

#### P6: 测试、文档（1.5 小时）

- [ ] 编写单元测试
- [ ] 编写集成测试
- [x] 更新 README
- [x] 部署文档（Docker配置）

### 10.3 里程碑

| 里程碑 | 完成标准 | 阶段 | 状态 |
|--------|---------|------|------|
| **M1: 可登录** | 用户可以注册、登录，获取 JWT | P0 + P1 | ✅ 完成 |
| **M2: 可管理** | 管理员可以管理用户、角色、部门 | P2 + P3 | ✅ 完成 |
| **M3: 可使用** | 用户可以通过代理使用 RAGForge，ACL 生效 | P4 | ✅ 完成 |
| **M4: 完整上线** | 前端集成完成，端到端流程通畅 | P5 + P6 | ✅ 完成 |

---

## 11. 部署方案

### 11.1 开发环境

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 初始化数据库
alembic upgrade head

# 5. 启动开发服务器
uvicorn app.main:app --reload --port 3001
```

### 11.2 环境变量

```bash
# .env.example

# 应用配置
APP_NAME=yaoyan-backend
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# 数据库（可与 RAGForge 共用同一 PostgreSQL 实例，不同数据库）
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/yaoyan

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# RAGForge 配置
RAGFORGE_BASE_URL=http://192.168.168.105:8020
RAGFORGE_ADMIN_KEY=kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ

# API Key 加密密钥
API_KEY_ENCRYPTION_KEY=your-aes-encryption-key

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### 11.3 生产部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  yaoyan-backend:
    build: .
    ports:
      - "3001:3001"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@db:5432/yaoyan
      - RAGFORGE_BASE_URL=http://ragforge:8020
    depends_on:
      - db
    
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=yaoyan

volumes:
  postgres_data:
```

### 11.4 与 RAGForge 共同部署

```
建议的部署架构：

┌─────────────────────────────────────────────┐
│              Docker Compose                  │
│                                              │
│  ┌────────────┐  ┌────────────┐             │
│  │  yaoyan    │  │  yaoyan    │             │
│  │  frontend  │  │  backend   │             │
│  │  :5173     │  │  :3001     │             │
│  └─────┬──────┘  └─────┬──────┘             │
│        │               │                     │
│        └───────┬───────┘                     │
│                │                             │
│  ┌─────────────┴─────────────┐              │
│  │       RAGForge            │              │
│  │       :8020               │              │
│  └─────────────┬─────────────┘              │
│                │                             │
│  ┌─────────────┴─────────────┐              │
│  │      PostgreSQL           │              │
│  │      :5432                │              │
│  │  ├── yaoyan (数据库)      │              │
│  │  └── ragforge (数据库)    │              │
│  └───────────────────────────┘              │
└─────────────────────────────────────────────┘
```

---

## 附录

### A. 参考资料

- [RAGForge 项目](file:///home/admin1/RAGForge/)
- [RAGForge 权限管理文档](file:///home/admin1/RAGForge/docs/PERMISSION_MANAGEMENT.md)
- [RAGForge API 文档](file:///home/admin1/RAGForge/docs/API_INTEGRATION.md)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/)

### B. 决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 后端语言 | Python / Node.js | **Python** | 与 RAGForge 技术栈一致 |
| Web 框架 | FastAPI / Flask | **FastAPI** | 异步、性能好、RAGForge 使用 |
| ORM | SQLAlchemy / Tortoise | **SQLAlchemy** | RAGForge 使用，成熟稳定 |
| 认证方式 | JWT / Session | **JWT** | 无状态，适合前后端分离 |
| API Key 存储 | 明文 / 加密 | **加密** | 安全性 |

### C. 待确认事项

1. **RAGForge API Key 更新**：RAGForge 是否支持更新已有 API Key 的 identity？
   - 如果不支持，需要删除旧 Key 创建新 Key
   
2. **共用数据库**：yaoyan 和 RAGForge 是否共用同一 PostgreSQL 实例？
   - 建议同一实例，不同数据库
   
3. **Admin Key 管理**：RAGForge Admin Key 的安全存储方案？

---

## 文档版本

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0 | 2026-01-26 | 初始版本 |
