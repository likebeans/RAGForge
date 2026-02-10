# RAGForge 文档索引

欢迎来到 RAGForge 文档中心。为了方便查阅，我们将文档按功能和层级进行了整理。

## 🚀 快速开始 (Getting Started)
- [快速开始](getting-started/quick-start.md): 5分钟运行第一个 Demo
- [环境配置](getting-started/configuration.md): 详细的 .env 配置说明
- [安装指南](getting-started/installation.md): Docker 与本地开发环境搭建
- [首次调用](getting-started/first-api-call.md): API 调用示例

## 🏗️ 架构设计 (Architecture)
- [架构概览](architecture/overview.md): 系统核心组件与运行拓扑
- [系统设计](architecture/system-design.md): 详细的子系统设计文档
- [Pipeline 架构](architecture/pipeline-architecture.md): 切分、检索、RAG 流程详解
- [API 规范](architecture/api-specification.md): RESTful API 设计准则
- [架构决策 (ADRs)](architecture/decisions.md): 关键架构决策记录
- [功能特性](architecture/features/rich-text-parser.md): 核心功能设计文档

## 📖 使用指南 (Guides)
- [部署指南](guides/deployment.md): 生产环境部署方案
- [API 集成](guides/api-integration.md): 核心 API 调用流程
- [权限管理](guides/permissions.md): 多租户与 ACL 权限配置
- [OpenAI SDK](guides/openai-sdk.md): 兼容接口使用指南
- [Admin Token](guides/admin-token-guide.md): 管理员接口使用说明
- [生产清单](guides/production-checklist.md): 上线前检查列表
- [数据迁移](guides/migration-sparse-es.md): BM25 到 ES 的迁移指南

## 👨‍💻 开发指南 (Development)
- [贡献指南](development/contributing.md): 代码规范与 PR 流程
- [多租户开发](development/multi-tenant-development.md): 租户隔离实现细节
- [Pipeline 开发](development/pipeline-development.md): 如何自定义 Chunker 和 Retriever
- [测试指南](development/testing.md): 单元测试与端到端测试
- [故障排查](development/troubleshooting.md): 常见问题解决方案

## 🛡️ 运维安全 (Operations)
- [安全运维](operations/security.md): 安全基线、凭据管理与威胁模型
- [监控指标](operations/monitoring.md): Prometheus 指标与日志
- [部署运维](operations/deployment.md): 日常运维手册

## 📊 报告与历史 (Reports)
- [项目评估](reports/assessment.md): 当前系统状态评估
- [优化报告](reports/optimization-test-report.md): 性能优化测试结果
- [历史阶段](reports/history/phase1.md): 项目演进历史

## 📚 SDK 文档
- [Python SDK](sdk/README.md): 客户端库使用说明

## 🌏 中文参考
- [中文文档索引](reference/chinese/index.md)
