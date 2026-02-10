# Phase 1: 核心功能重构与增强

## 目标
建立稳固的基础架构，实现核心 RAG 流程的端到端跑通。

## 任务列表

### 1. 基础设施
- [x] 初始化 FastAPI 项目结构
- [x] 配置 PostgreSQL + pgvector
- [x] 集成 Alembic 数据库迁移
- [x] 实现基础日志系统

### 2. 核心服务
- [x] 实现文档上传与存储 API
- [x] 开发基础切分器 (Simple, Recursive)
- [x] 集成 OpenAI/Ollama Embedding 接口
- [x] 实现向量存储与检索逻辑

### 3. API 网关
- [x] 设计 RESTful API 规范
- [x] 实现 API Key 认证与权限控制
- [x] 添加请求校验 (Pydantic)

### 4. 测试
- [x] 编写单元测试框架
- [x] 完成核心流程的集成测试

## 成果
完成 MVP 版本，支持基本的文档上传、切分、索引和问答功能。
