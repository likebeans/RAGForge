# 入门指南

欢迎使用 Self-RAG Pipeline！本指南将帮助您快速上手，从安装部署到第一个 API 调用。

## 概述

Self-RAG Pipeline 是一个企业级的多租户知识库检索服务，提供 OpenAI 兼容的 API 接口。无论您是开发者、系统管理员还是产品经理，都可以通过本指南快速了解和使用这个强大的 RAG 平台。

## 学习路径

### 🚀 快速体验（5 分钟）

如果您想快速体验 Self-RAG Pipeline 的功能：

1. **[快速开始](./quick-start)** - 使用 Docker Compose 一键启动
2. **[第一个 API 调用](./first-api-call)** - 体验 OpenAI 兼容接口

### 📚 完整部署（30 分钟）

如果您计划在生产环境中使用：

1. **[安装指南](./installation)** - 详细的安装和依赖配置
2. **[配置指南](./configuration)** - 环境变量和高级配置
3. **[第一个 API 调用](./first-api-call)** - 验证部署结果

## 核心概念

在开始之前，了解这些核心概念将帮助您更好地使用 Self-RAG Pipeline：

### 租户（Tenant）
- 多租户架构的基本单位
- 每个租户拥有独立的知识库和 API Key
- 支持租户级别的配额和权限管理

### 知识库（Knowledge Base）
- 文档和知识的容器
- 每个知识库可以配置不同的算法参数
- 支持多种文档格式和切分策略

### 检索算法
- **稠密检索**：基于语义向量的相似度搜索
- **BM25**：基于关键词的传统搜索算法
- **混合检索**：结合稠密和稀疏检索的优势
- **RAPTOR**：多层次递归摘要索引

### API 接口
- **OpenAI 兼容**：支持 Chat Completions 和 Embeddings
- **原生接口**：提供更多高级功能和配置选项
- **Python SDK**：完整的客户端库

## 系统要求

### 最低要求
- **CPU**：2 核心
- **内存**：4GB RAM
- **存储**：10GB 可用空间
- **操作系统**：Linux、macOS 或 Windows（支持 Docker）

### 推荐配置
- **CPU**：4+ 核心
- **内存**：8GB+ RAM
- **存储**：50GB+ SSD
- **网络**：稳定的互联网连接（用于下载模型）

### 依赖服务
- **PostgreSQL 12+**：元数据存储
- **Qdrant 1.7+**：向量数据库（默认）
- **Docker & Docker Compose**：容器化部署

## 支持的功能

### ✅ 已支持
- 多租户管理和隔离
- OpenAI 兼容 API 接口
- 多种检索算法（Dense、BM25、Hybrid、RAPTOR）
- 多 LLM 提供商支持
- Python SDK
- 完整的监控和日志
- Docker 部署

### 🚧 开发中
- Web 管理界面优化
- 更多向量数据库支持
- 高级 RAG 策略
- 性能优化工具

### 📋 计划中
- 多语言 SDK
- 图形化配置界面
- 自动化测试工具
- 企业级安全增强

## 获取帮助

遇到问题？这里有一些资源可以帮助您：

- **📖 文档**：查看详细的 [开发文档](../development/) 和 [架构文档](../architecture/)
- **🐛 问题反馈**：在 GitHub 上提交 [Issue](https://github.com/your-org/self-rag-pipeline/issues)
- **💬 社区讨论**：加入我们的社区讨论
- **📧 技术支持**：联系技术支持团队

## 下一步

选择适合您的学习路径：

::: tip 推荐路径
对于大多数用户，我们推荐从 **[快速开始](./quick-start)** 开始，然后根据需要深入学习其他内容。
:::

- **开发者** → [快速开始](./quick-start) → [API 调用](./first-api-call) → [开发文档](../development/)
- **运维人员** → [安装指南](./installation) → [配置指南](./configuration) → [运维文档](../operations/)
- **架构师** → [系统架构](../architecture/) → [API 规范](../architecture/api-specification)

---

准备好开始了吗？让我们从 [快速开始](./quick-start) 开始您的 Self-RAG Pipeline 之旅！