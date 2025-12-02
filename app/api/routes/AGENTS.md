# Routes 路由定义模块

各功能的 HTTP 路由端点定义。

## 模块职责

- 定义 RESTful API 端点
- 参数验证和转换
- 调用 services 层

## 路由文件

| 文件 | 前缀 | 说明 |
|------|------|------|
| `health.py` | `/health` | 健康检查，无需认证 |
| `api_keys.py` | `/v1/api-keys` | API Key CRUD |
| `kb.py` | `/v1/knowledge-bases` | 知识库 CRUD |
| `documents.py` | `/v1/documents` | 文档上传和管理 |
| `query.py` | `/v1/query` | 知识库检索 |

## API 端点一览

### 健康检查
```
GET  /health              # 服务状态
```

### API Key 管理
```
POST   /v1/api-keys       # 创建 Key
GET    /v1/api-keys       # 列出 Keys
DELETE /v1/api-keys/{id}  # 删除 Key
```

### 知识库管理
```
POST   /v1/knowledge-bases       # 创建知识库
GET    /v1/knowledge-bases       # 列出知识库
GET    /v1/knowledge-bases/{id}  # 获取详情
DELETE /v1/knowledge-bases/{id}  # 删除知识库
```

### 文档管理
```
POST   /v1/documents              # 上传文档
GET    /v1/documents              # 列出文档
DELETE /v1/documents/{id}         # 删除文档
```

### 检索
```
POST   /v1/query                  # 执行检索
```

## 路由模板

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_tenant
from app.models import Tenant
from app.schemas.my_feature import MyCreate, MyResponse

router = APIRouter(prefix="/v1/my-feature", tags=["my-feature"])

@router.post("/", response_model=MyResponse)
async def create_item(
    data: MyCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    # 调用 service
    result = await my_service(db, tenant.id, data)
    return result

@router.get("/{item_id}", response_model=MyResponse)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    item = await get_item_by_id(db, tenant.id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

## 注册新路由

在 `__init__.py` 中添加：

```python
from app.api.routes.my_feature import router as my_feature_router

api_router.include_router(my_feature_router)
```

## 注意事项

- 除 `/health` 外，所有路由需要认证
- 使用 `tags` 参数分组 OpenAPI 文档
- 错误使用 `HTTPException` 抛出
- 复杂逻辑放在 services 层
