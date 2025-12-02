# Schemas 数据模型模块

Pydantic 请求/响应模型定义。

## 模块职责

- 定义 API 请求体结构
- 定义 API 响应体结构
- 数据验证和序列化

## 核心文件

| 文件 | 说明 |
|------|------|
| `api_key.py` | API Key 相关 schema |
| `kb.py` | 知识库相关 schema |
| `document.py` | 文档相关 schema |
| `query.py` | 检索相关 schema |

## Schema 命名规范

| 后缀 | 用途 | 示例 |
|------|------|------|
| `Create` | 创建请求 | `KnowledgeBaseCreate` |
| `Update` | 更新请求 | `KnowledgeBaseUpdate` |
| `Response` | 响应模型 | `KnowledgeBaseResponse` |
| `List` | 列表响应 | `KnowledgeBaseList` |

## 使用示例

### 定义 Schema
```python
from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class ItemResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # 支持从 ORM 对象转换
```

### 在路由中使用
```python
@router.post("/items", response_model=ItemResponse)
async def create_item(data: ItemCreate, db: AsyncSession = Depends(get_db)):
    item = Item(**data.model_dump())
    db.add(item)
    await db.commit()
    return item
```

## 常用字段验证

```python
from pydantic import Field, validator

class MySchema(BaseModel):
    # 字符串长度限制
    name: str = Field(..., min_length=1, max_length=100)
    
    # 数值范围
    top_k: int = Field(default=5, ge=1, le=100)
    
    # 可选字段
    description: str | None = None
    
    # 列表
    kb_ids: list[str] = Field(..., min_length=1)
    
    # 自定义验证
    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()
```

## 注意事项

- 请求模型必须验证所有输入
- 响应模型设置 `from_attributes = True` 以支持 ORM 转换
- 敏感字段（如密码哈希）不应出现在响应模型中
- 使用 `Field` 提供字段描述，自动生成 OpenAPI 文档
