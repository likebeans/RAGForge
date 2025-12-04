# API 路由模块

FastAPI 路由层，定义 HTTP 接口和请求处理逻辑。

## 模块职责

- 定义 RESTful API 端点
- 请求参数验证（通过 Pydantic schemas）
- 依赖注入（认证、数据库会话）
- 调用 services 层处理业务逻辑

## 核心文件

| 文件 | 说明 |
|------|------|
| `deps.py` | 依赖注入函数（get_db, verify_admin_token, require_role） |
| `routes/` | 各功能路由模块 |

## 路由端点

| 路由文件 | 前缀 | 功能 |
|----------|------|------|
| `health.py` | `/health` | 健康检查 |
| `admin.py` | `/admin` | 租户/API Key 管理（需 Admin Token） |
| `api_keys.py` | `/v1/api-keys` | API Key 管理（租户自管理） |
| `kb.py` | `/v1/knowledge-bases` | 知识库管理 |
| `documents.py` | `/v1/knowledge-bases/{kb_id}/documents` | 文档上传和管理 |
| `query.py` | `/v1/retrieve` | 知识库检索 |

## 依赖注入

```python
from app.api.deps import get_db, get_current_tenant

@router.get("/example")
async def example(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    # db: 异步数据库会话
    # tenant: 当前请求的租户（通过 API Key 认证）
    pass
```

## 认证流程

1. 请求携带 `Authorization: Bearer <api_key>` 头
2. `get_current_tenant` 依赖验证 API Key
3. 返回关联的 Tenant 对象
4. 所有数据操作限定在该租户范围内

## 添加新路由

1. 在 `routes/` 下创建新文件
2. 使用 `APIRouter` 定义路由
3. 在 `routes/__init__.py` 中注册到主路由

```python
# routes/my_feature.py
from fastapi import APIRouter, Depends
from app.api.deps import get_db, get_current_tenant

router = APIRouter(prefix="/v1/my-feature", tags=["my-feature"])

@router.get("/")
async def list_items(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    pass
```

## 注意事项

- 所有接口需要 API Key 认证（除 `/health`）
- 使用 Pydantic schemas 定义请求/响应模型
- 业务逻辑应放在 `services/` 层，路由层只做参数处理
- 检索接口 `/v1/retrieve` 会先完成向量/BM25 检索，再做 ACL 过滤；如果命中但被 ACL 全部过滤，会返回 `403` (`code=NO_PERMISSION`)，请检查文档敏感度与 API Key 的 identity/clearance 或调整文档 ACL。
