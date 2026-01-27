# 药研 AI 平台产品方案（第四部分）

## 目录

- [7. 技术实现详细方案](#7-技术实现详细方案)

---

## 7. 技术实现详细方案

### 7.1 系统架构设计

#### 7.1.1 整体架构

采用**微服务架构**，将系统划分为多个独立的服务模块，每个模块负责特定的业务功能。

```
┌─────────────────────────────────────────────────────────────┐
│                         客户端层                              │
│  - Web 浏览器（React SPA）                                    │
│  - 移动浏览器（响应式）                                        │
│  - API 客户端（第三方集成）                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓ HTTPS
┌─────────────────────────────────────────────────────────────┐
│                      API 网关层                               │
│  Nginx / Kong                                                │
│  - 反向代理                                                   │
│  - 负载均衡                                                   │
│  - SSL 终止                                                   │
│  - 请求路由                                                   │
│  - 限流熔断                                                   │
│  - 日志记录                                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      应用服务层                               │
│  FastAPI (Python 3.11+)                                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 用户服务      │  │ 项目服务      │  │ 文档服务      │      │
│  │ - 认证授权    │  │ - 项目管理    │  │ - 上传下载    │      │
│  │ - 用户管理    │  │ - 成员管理    │  │ - 版本控制    │      │
│  │ - 角色权限    │  │ - 筛选查询    │  │ - 预览转换    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 实验服务      │  │ 检索服务      │  │ 问答服务      │      │
│  │ - 实验记录    │  │ - 全文检索    │  │ - RAG 问答    │      │
│  │ - 数据管理    │  │ - 语义检索    │  │ - 对话管理    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ 审计服务      │  │ 导入导出服务  │                        │
│  │ - 日志记录    │  │ - Excel 处理  │                        │
│  │ - 审计查询    │  │ - 批量操作    │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      异步任务层                               │
│  Celery + Redis                                              │
│  - 文档处理（文本提取、向量化）                                │
│  - 数据导入导出                                               │
│  - 报表生成                                                   │
│  - 定时任务                                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │ MinIO        │  │ Milvus       │      │
│  │ - 关系数据    │  │ - 文档存储    │  │ - 向量存储    │      │
│  │ - 元数据      │  │ - 对象存储    │  │ - 相似度检索  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Redis        │  │ Elasticsearch│                        │
│  │ - 缓存        │  │ - 全文检索    │                        │
│  │ - 会话        │  │ - 日志存储    │                        │
│  │ - 消息队列    │  │ (可选)       │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      AI 服务层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LLM API      │  │ Embedding    │  │ Rerank       │      │
│  │ - GPT-4      │  │ - text-emb-3 │  │ - 结果重排    │      │
│  │ - Claude     │  │ - BGE        │  │              │      │
│  │ - 本地模型    │  │ - M3E        │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

#### 7.1.2 技术选型理由

**前端技术栈**：
- **React**：成熟的前端框架，生态丰富，社区活跃
- **Vite**：快速的构建工具，开发体验好
- **TailwindCSS**：实用优先的 CSS 框架，开发效率高
- **shadcn/ui**：高质量的 React 组件库，可定制性强

**后端技术栈**：
- **FastAPI**：
  - 高性能（基于 Starlette 和 Pydantic）
  - 自动生成 API 文档（OpenAPI）
  - 类型提示和数据验证
  - 异步支持
  - 易于测试
- **SQLAlchemy**：成熟的 Python ORM，支持多种数据库
- **Celery**：分布式任务队列，支持异步任务

**数据存储**：
- **PostgreSQL**：
  - 成熟稳定的关系数据库
  - 支持 JSON、全文检索等高级特性
  - 强大的事务支持
  - 适合存储结构化数据
- **MinIO**：
  - S3 兼容的对象存储
  - 开源免费
  - 易于部署和扩展
  - 适合存储大文件
- **Milvus**：
  - 专为向量检索设计
  - 高性能、可扩展
  - 支持多种索引类型
  - 适合 AI 应用
- **Redis**：
  - 高性能内存数据库
  - 支持多种数据结构
  - 适合缓存和会话管理

### 7.2 数据流设计

#### 7.2.1 文档上传流程

```
用户上传文档
    ↓
前端验证（文件类型、大小）
    ↓
上传到后端 API
    ↓
后端验证和权限检查
    ↓
保存元数据到 PostgreSQL
    ↓
上传文件到 MinIO
    ↓
创建异步任务（Celery）
    ↓
┌─────────────────────────────┐
│ 异步任务处理：                │
│ 1. 文本提取                  │
│ 2. 文本分块（Chunking）       │
│ 3. 向量化（Embedding）        │
│ 4. 存储向量到 Milvus         │
│ 5. 更新索引状态              │
└─────────────────────────────┘
    ↓
返回上传成功
```

#### 7.2.2 智能问答流程

```
用户提问
    ↓
前端发送问题到后端
    ↓
后端接收问题
    ↓
权限检查（用户可访问的文档范围）
    ↓
问题向量化（Embedding）
    ↓
在 Milvus 中检索相关文档片段
    ↓
权限过滤（只返回用户有权访问的片段）
    ↓
（可选）重排序（Rerank）
    ↓
构建 Prompt（问题 + 上下文）
    ↓
调用 LLM API
    ↓
流式返回答案（SSE）
    ↓
记录对话历史
    ↓
记录审计日志
```

#### 7.2.3 权限检查流程

```
用户请求资源
    ↓
提取用户身份（JWT Token）
    ↓
检查 Redis 缓存中的权限
    ↓
缓存命中？
    ├─ 是 → 返回权限结果
    └─ 否 → 查询数据库
            ↓
        计算用户权限：
        - 用户直接权限
        - 角色权限
        - 组权限
        - 项目成员权限
            ↓
        缓存到 Redis（TTL: 5分钟）
            ↓
        返回权限结果
    ↓
允许访问？
    ├─ 是 → 执行操作
    └─ 否 → 返回 403 错误
```

### 7.3 数据库设计

#### 7.3.1 核心表结构

**用户表（users）**：
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    department VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**角色表（roles）**：
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用户角色关联表（user_roles）**：
```sql
CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
```

**组表（groups）**：
```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,
    group_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用户组关联表（user_groups）**：
```sql
CREATE TABLE user_groups (
    user_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    PRIMARY KEY (user_id, group_id)
);
```

**项目表（drug_projects）**：
```sql
CREATE TABLE drug_projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) UNIQUE NOT NULL,
    project_name VARCHAR(200) NOT NULL,
    drug_type VARCHAR(50),
    indication VARCHAR(100),
    target VARCHAR(100),
    stage VARCHAR(50),
    status VARCHAR(50),
    priority VARCHAR(20),
    start_date DATE,
    end_date DATE,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**项目成员表（project_members）**：
```sql
CREATE TABLE project_members (
    project_id INTEGER REFERENCES drug_projects(id),
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(50),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
);
```

**文档表（documents）**：
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    document_code VARCHAR(50) UNIQUE,
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    file_path VARCHAR(1000),
    description TEXT,
    tags TEXT[],
    category VARCHAR(100),
    sensitivity_level VARCHAR(50),
    version VARCHAR(20) DEFAULT '1.0',
    parent_id INTEGER REFERENCES documents(id),
    project_id INTEGER REFERENCES drug_projects(id),
    uploader_id INTEGER REFERENCES users(id),
    indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**实验表（experiments）**：
```sql
CREATE TABLE experiments (
    id SERIAL PRIMARY KEY,
    experiment_code VARCHAR(50) UNIQUE NOT NULL,
    experiment_name VARCHAR(200) NOT NULL,
    project_id INTEGER REFERENCES drug_projects(id),
    experiment_type VARCHAR(50),
    purpose TEXT,
    method TEXT,
    materials TEXT,
    procedure TEXT,
    results TEXT,
    conclusion TEXT,
    experimenter_id INTEGER REFERENCES users(id),
    experiment_date DATE,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**权限表（permissions）**：
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    subject_type VARCHAR(50) NOT NULL,
    subject_id INTEGER NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER NOT NULL,
    permission_type VARCHAR(50) NOT NULL,
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE (subject_type, subject_id, resource_type, resource_id, permission_type)
);
```

**审计日志表（audit_logs）**：
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

**数据字典表（dict_items）**：
```sql
CREATE TABLE dict_items (
    id SERIAL PRIMARY KEY,
    dict_type VARCHAR(50) NOT NULL,
    dict_value VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    display_order INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dict_type, dict_value)
);
```

#### 7.3.2 索引设计

```sql
-- 用户表索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- 项目表索引
CREATE INDEX idx_projects_code ON drug_projects(project_code);
CREATE INDEX idx_projects_owner ON drug_projects(owner_id);
CREATE INDEX idx_projects_stage ON drug_projects(stage);
CREATE INDEX idx_projects_status ON drug_projects(status);

-- 文档表索引
CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_uploader ON documents(uploader_id);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_created ON documents(created_at);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);

-- 实验表索引
CREATE INDEX idx_experiments_project ON experiments(project_id);
CREATE INDEX idx_experiments_experimenter ON experiments(experimenter_id);
CREATE INDEX idx_experiments_date ON experiments(experiment_date);
```

### 7.4 API 设计

#### 7.4.1 API 规范

**RESTful API 设计原则**：
- 使用标准 HTTP 方法（GET, POST, PUT, DELETE）
- 使用名词复数形式表示资源（/api/projects, /api/documents）
- 使用路径参数表示资源 ID（/api/projects/{id}）
- 使用查询参数进行筛选和分页（?page=1&size=20）
- 返回标准 HTTP 状态码

**统一响应格式**：
```json
{
  "code": 200,
  "message": "Success",
  "data": { ... },
  "timestamp": "2024-01-27T10:00:00Z"
}
```

**错误响应格式**：
```json
{
  "code": 400,
  "message": "Validation error",
  "errors": [
    {
      "field": "project_name",
      "message": "Project name is required"
    }
  ],
  "timestamp": "2024-01-27T10:00:00Z"
}
```

#### 7.4.2 核心 API 端点

**认证与授权**：
```
POST   /api/auth/login          # 用户登录
POST   /api/auth/logout         # 用户登出
POST   /api/auth/refresh        # 刷新 Token
GET    /api/auth/me             # 获取当前用户信息
```

**用户管理**：
```
GET    /api/users               # 获取用户列表
GET    /api/users/{id}          # 获取用户详情
POST   /api/users               # 创建用户
PUT    /api/users/{id}          # 更新用户
DELETE /api/users/{id}          # 删除用户
```

**项目管理**：
```
GET    /api/projects            # 获取项目列表（支持筛选）
GET    /api/projects/{id}       # 获取项目详情
POST   /api/projects            # 创建项目
PUT    /api/projects/{id}       # 更新项目
DELETE /api/projects/{id}       # 删除项目
GET    /api/projects/{id}/members        # 获取项目成员
POST   /api/projects/{id}/members        # 添加项目成员
DELETE /api/projects/{id}/members/{uid}  # 移除项目成员
GET    /api/projects/{id}/dashboard      # 获取项目仪表板
POST   /api/projects/import     # 导入项目
GET    /api/projects/export     # 导出项目
```

**文档管理**：
```
GET    /api/documents           # 获取文档列表
GET    /api/documents/{id}      # 获取文档详情
POST   /api/documents           # 上传文档
PUT    /api/documents/{id}      # 更新文档元数据
DELETE /api/documents/{id}      # 删除文档
GET    /api/documents/{id}/download     # 下载文档
GET    /api/documents/{id}/preview      # 预览文档
GET    /api/documents/{id}/versions     # 获取文档版本列表
POST   /api/documents/{id}/versions     # 上传新版本
```

**实验管理**：
```
GET    /api/experiments         # 获取实验列表
GET    /api/experiments/{id}    # 获取实验详情
POST   /api/experiments         # 创建实验
PUT    /api/experiments/{id}    # 更新实验
DELETE /api/experiments/{id}    # 删除实验
```

**检索与问答**：
```
GET    /api/search              # 全文检索
POST   /api/semantic-search     # 语义检索
POST   /api/chat                # 智能问答
GET    /api/chat/history        # 获取对话历史
```

**权限管理**：
```
GET    /api/permissions         # 获取权限列表
POST   /api/permissions         # 授予权限
DELETE /api/permissions/{id}    # 撤销权限
POST   /api/permission-requests # 申请权限
GET    /api/permission-requests # 获取权限申请列表
PUT    /api/permission-requests/{id}  # 审批权限申请
```

**审计日志**：
```
GET    /api/audit-logs          # 获取审计日志
GET    /api/audit-logs/export   # 导出审计日志
```

**数据字典**：
```
GET    /api/dict-items          # 获取数据字典
POST   /api/dict-items          # 创建字典项
PUT    /api/dict-items/{id}     # 更新字典项
DELETE /api/dict-items/{id}     # 删除字典项
```

### 7.5 AI 集成方案

#### 7.5.1 文档向量化

**文本提取**：
```python
def extract_text(file_path: str, file_type: str) -> str:
    if file_type == 'pdf':
        return extract_pdf_text(file_path)
    elif file_type in ['docx', 'doc']:
        return extract_word_text(file_path)
    elif file_type in ['xlsx', 'xls']:
        return extract_excel_text(file_path)
    elif file_type == 'txt':
        return read_text_file(file_path)
    else:
        raise UnsupportedFileTypeError(file_type)
```

**文本分块（Chunking）**：
```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    将长文本分割成小块，便于向量化和检索
    
    Args:
        text: 原始文本
        chunk_size: 每块的字符数
        overlap: 块之间的重叠字符数
    
    Returns:
        文本块列表
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks
```

**向量化**：
```python
async def embed_text(text: str) -> List[float]:
    """
    将文本转换为向量
    
    使用 OpenAI text-embedding-3-small 模型
    """
    response = await openai.Embedding.acreate(
        model="text-embedding-3-small",
        input=text
    )
    return response['data'][0]['embedding']
```

**存储到 Milvus**：
```python
async def store_document_vectors(
    document_id: int,
    chunks: List[str],
    vectors: List[List[float]]
):
    """
    将文档向量存储到 Milvus
    """
    collection = milvus_client.get_collection("documents")
    
    entities = [
        {
            "document_id": document_id,
            "chunk_index": i,
            "chunk_text": chunk,
            "vector": vector
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    
    collection.insert(entities)
```

#### 7.5.2 RAG 实现

**检索相关文档**：
```python
async def retrieve_relevant_chunks(
    query: str,
    user_id: int,
    top_k: int = 5
) -> List[Dict]:
    """
    检索与查询相关的文档片段
    """
    # 1. 向量化查询
    query_vector = await embed_text(query)
    
    # 2. 在 Milvus 中检索
    collection = milvus_client.get_collection("documents")
    results = collection.search(
        data=[query_vector],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k * 2  # 多检索一些，用于权限过滤
    )
    
    # 3. 权限过滤
    document_ids = [r.entity.get("document_id") for r in results[0]]
    accessible_docs = await get_accessible_documents(user_id, document_ids)
    
    # 4. 过滤并返回
    filtered_results = [
        r for r in results[0]
        if r.entity.get("document_id") in accessible_docs
    ][:top_k]
    
    return [
        {
            "document_id": r.entity.get("document_id"),
            "chunk_text": r.entity.get("chunk_text"),
            "score": r.distance
        }
        for r in filtered_results
    ]
```

**构建 Prompt**：
```python
def build_rag_prompt(query: str, chunks: List[Dict]) -> str:
    """
    构建 RAG Prompt
    """
    context = "\n\n".join([
        f"文档 {i+1}:\n{chunk['chunk_text']}"
        for i, chunk in enumerate(chunks)
    ])
    
    prompt = f"""你是一个药物研发领域的专家助手。请基于以下文档内容回答用户的问题。

文档内容：
---
{context}
---

用户问题：{query}

请提供准确、专业的回答。如果文档中没有相关信息，请明确说明。在回答中标注信息来源（文档编号）。
"""
    return prompt
```

**调用 LLM**：
```python
async def generate_answer(prompt: str) -> AsyncIterator[str]:
    """
    调用 LLM 生成答案（流式）
    """
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "你是一个药物研发领域的专家助手。"},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.get("content"):
            yield chunk.choices[0].delta.content
```

**完整的问答流程**：
```python
async def answer_question(query: str, user_id: int) -> AsyncIterator[str]:
    """
    完整的 RAG 问答流程
    """
    # 1. 检索相关文档
    chunks = await retrieve_relevant_chunks(query, user_id)
    
    # 2. 构建 Prompt
    prompt = build_rag_prompt(query, chunks)
    
    # 3. 生成答案（流式）
    async for token in generate_answer(prompt):
        yield token
    
    # 4. 记录对话历史
    await save_chat_history(user_id, query, chunks)
```

### 7.6 安全实现

#### 7.6.1 认证实现

**JWT Token 生成**：
```python
def create_access_token(user_id: int, expires_delta: timedelta = None) -> str:
    """
    创建 JWT Access Token
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token
```

**Token 验证**：
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    从 Token 中获取当前用户
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        
        user = await get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### 7.6.2 权限检查实现

**权限装饰器**：
```python
def require_permission(
    resource_type: str,
    permission_type: str
):
    """
    权限检查装饰器
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户
            user = kwargs.get('current_user')
            
            # 获取资源 ID
            resource_id = kwargs.get('id') or kwargs.get('resource_id')
            
            # 检查权限
            has_permission = await check_permission(
                user.id,
                resource_type,
                resource_id,
                permission_type
            )
            
            if not has_permission:
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
```

**权限检查逻辑**：
```python
async def check_permission(
    user_id: int,
    resource_type: str,
    resource_id: int,
    permission_type: str
) -> bool:
    """
    检查用户是否有权限
    """
    # 1. 检查缓存
    cache_key = f"permission:{user_id}:{resource_type}:{resource_id}:{permission_type}"
    cached = await redis_client.get(cache_key)
    if cached is not None:
        return cached == "1"
    
    # 2. 检查直接权限
    has_direct = await has_direct_permission(user_id, resource_type, resource_id, permission_type)
    
    # 3. 检查角色权限
    has_role = await has_role_permission(user_id, resource_type, permission_type)
    
    # 4. 检查组权限
    has_group = await has_group_permission(user_id, resource_type, resource_id, permission_type)
    
    # 5. 检查项目成员权限
    has_project = await has_project_permission(user_id, resource_type, resource_id, permission_type)
    
    # 6. 综合判断
    result = has_direct or has_role or has_group or has_project
    
    # 7. 缓存结果
    await redis_client.setex(cache_key, 300, "1" if result else "0")
    
    return result
```

#### 7.6.3 数据加密

**敏感数据加密**：
```python
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str) -> str:
    """
    加密敏感数据
    """
    cipher = Fernet(ENCRYPTION_KEY)
    encrypted = cipher.encrypt(data.encode())
    return encrypted.decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    解密敏感数据
    """
    cipher = Fernet(ENCRYPTION_KEY)
    decrypted = cipher.decrypt(encrypted_data.encode())
    return decrypted.decode()
```

**密码哈希**：
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    哈希密码
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    """
    return pwd_context.verify(plain_password, hashed_password)
```

### 7.7 性能优化

#### 7.7.1 缓存策略

**多级缓存**：
```
L1: 应用内存缓存（LRU Cache）
    ↓ 未命中
L2: Redis 缓存（5-30 分钟 TTL）
    ↓ 未命中
L3: 数据库查询
```

**缓存内容**：
- 用户信息和权限（TTL: 5 分钟）
- 数据字典（TTL: 30 分钟）
- 热门文档元数据（TTL: 10 分钟）
- 项目信息（TTL: 10 分钟）
- 检索结果（TTL: 5 分钟）

#### 7.7.2 数据库优化

**连接池**：
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=3600
)
```

**查询优化**：
- 使用索引
- 避免 N+1 查询（使用 joinedload）
- 分页查询
- 只查询需要的字段

**读写分离**（可选）：
- 主库：写操作
- 从库：读操作

#### 7.7.3 异步处理

**异步任务**：
- 文档处理（文本提取、向量化）
- 数据导入导出
- 报表生成
- 邮件发送

**任务优先级**：
- 高优先级：用户交互相关（如文档预览转换）
- 中优先级：后台处理（如向量化）
- 低优先级：定时任务（如数据统计）

---

**（第四部分完）**

下一部分将包含：数据指标、风险分析和实施路线图。
