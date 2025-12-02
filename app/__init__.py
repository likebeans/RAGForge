"""
RAG Pipeline Service - 应用主包

这是知识库服务的核心应用包，包含以下子模块：
- api/      : API 路由和依赖注入
- auth/     : 认证授权（API Key、JWT）
- db/       : 数据库连接和会话管理
- models/   : SQLAlchemy ORM 数据模型
- schemas/  : Pydantic 请求/响应模式
- services/ : 业务逻辑服务层
- infra/    : 基础设施（向量库、Embedding）

项目架构遵循分层设计：
    API层 → 服务层 → 数据访问层 → 基础设施层
"""
