# 文档索引

欢迎来到 Self-RAG Pipeline 项目文档中心。本页面提供完整的文档导航和索引。

## 🚀 快速开始

快速上手项目的必读文档：

- **[安装指南](getting-started/installation.md)** - 环境准备和依赖安装
- **[快速开始](getting-started/quick-start.md)** - 5 分钟快速体验
- **[配置说明](getting-started/configuration.md)** - 环境变量和配置项
- **[第一个 API 调用](getting-started/first-api-call.md)** - API 使用示例

## 📖 使用指南

详细的使用指南和最佳实践：

### 配置和部署
- **[环境配置指南](guides/environment-config.md)** - 环境变量管理、配置文件详解
- **[生产环境检查清单](guides/production-checklist.md)** - 上线前完整检查
- **[部署指南](guides/deployment.md)** - 生产环境部署步骤

### 认证和权限
- **[Admin Token 使用指南](guides/admin-token-guide.md)** - Admin API 认证和管理

### SDK 和集成
- **[OpenAI SDK 指南](guides/openai-sdk.md)** - OpenAI 兼容 API 使用
- **[Python SDK 文档](sdk/README.md)** - Python 客户端库

### 迁移和升级
- **[BM25 迁移指南](guides/migration-sparse-es.md)** - OpenSearch/ES 迁移

[查看所有指南 →](guides/)

## 🏗️ 架构设计

系统架构和设计文档：

- **[系统设计](architecture/system-design.md)** - 整体架构设计
- **[Pipeline 架构](architecture/pipeline-architecture.md)** - 算法框架设计
- **[API 规范](architecture/api-specification.md)** - RESTful API 设计
- **[架构决策](architecture/decisions.md)** - 重要设计决策记录
- **[架构更新记录](architecture/architecture-updates.md)** - 架构变更历史

## 👨‍💻 开发文档

面向开发者的文档：

- **[贡献指南](development/contributing.md)** - 如何参与项目开发
- **[多租户开发](development/multi-tenant-development.md)** - 多租户功能开发
- **[Pipeline 开发](development/pipeline-development.md)** - 算法组件开发
- **[测试指南](development/testing.md)** - 单元测试、集成测试
- **[故障排查](development/troubleshooting.md)** - 常见问题解决

## 🔧 运维文档

生产环境运维和监控：

- **[部署指南](operations/deployment.md)** - 部署策略和流程
- **[监控指南](operations/monitoring.md)** - 系统监控和告警
- **[安全指南](operations/security.md)** - 安全配置和最佳实践
- **[故障排查](operations/troubleshooting.md)** - 运维故障处理

## 📊 报告和总结

项目报告和历史记录：

- **[代码审查报告](reports/code-review-report.md)** - 代码质量审查
- **[改进完成报告](reports/improvements-completed.md)** - 改进项目总结
- **[测试总结](reports/test-summary.md)** - 测试覆盖和结果
- **[OpenAI SDK 测试](reports/openai-sdk-testing.md)** - SDK 测试报告
- **[设计调整日志](reports/design-adjustments.md)** - 设计变更记录
- **[人工验证报告](reports/manual-verification.md)** - 功能验证报告

[查看所有报告 →](reports/)

## 📚 参考文档

### 中文参考文档
- **[API 设计](reference/chinese/api-design.md)** - API 设计原则
- **[开发指南](reference/chinese/development.md)** - 中文开发文档
- **[优化经验](reference/chinese/optimization.md)** - 性能优化实践
- **[实践总结](reference/chinese/practice-summary.md)** - 开发实践总结
- **[租户开发](reference/chinese/tenant-development.md)** - 多租户开发经验
- **[测试记录](reference/chinese/test-records.md)** - 测试活动记录
- **[部署经验](reference/chinese/deployment.md)** - 部署实践
- **[向量维度修复](reference/chinese/vector-dimension-fix.md)** - 问题修复记录

### 历史文档
- **[Phase 1](reference/history/phase1.md)** - 项目第一阶段
- **[Phase 2](reference/history/phase2.md)** - 项目第二阶段
- **[Phase 3](reference/history/phase3.md)** - 项目第三阶段

## 🔗 外部文档

- **[主 README](../README.md)** - 项目主文档（英文）
- **[中文 README](../README.zh-CN.md)** - 项目主文档（中文）
- **[开发助手文档](../AGENTS.md)** - AI 编程助手指南
- **[Frontend 文档](../frontend/README.md)** - 前端项目文档
- **[SDK 源码文档](../sdk/README.md)** - SDK 项目文档

## 📋 文档目录结构

```
docs/
├── index.md                 # VitePress 主页
├── documentation.md         # 文档索引（本页面）
├── getting-started/         # 快速开始
│   ├── installation.md
│   ├── quick-start.md
│   ├── configuration.md
│   └── first-api-call.md
├── guides/                  # 使用指南
│   ├── README.md
│   ├── admin-token-guide.md
│   ├── environment-config.md
│   ├── openai-sdk.md
│   ├── production-checklist.md
│   ├── deployment.md
│   └── migration-sparse-es.md
├── architecture/            # 架构设计
│   ├── system-design.md
│   ├── pipeline-architecture.md
│   ├── api-specification.md
│   ├── decisions.md
│   └── architecture-updates.md
├── development/             # 开发文档
│   ├── contributing.md
│   ├── multi-tenant-development.md
│   ├── pipeline-development.md
│   ├── testing.md
│   └── troubleshooting.md
├── operations/              # 运维文档
│   ├── deployment.md
│   ├── monitoring.md
│   ├── security.md
│   └── troubleshooting.md
├── reports/                 # 报告总结
│   ├── README.md
│   ├── code-review-report.md
│   ├── improvements-completed.md
│   ├── test-summary.md
│   ├── openai-sdk-testing.md
│   ├── design-adjustments.md
│   └── manual-verification.md
├── reference/               # 参考文档
│   ├── chinese/            # 中文参考
│   └── history/            # 历史文档
└── sdk/                     # SDK 文档
    └── README.md
```

## 🤝 贡献文档

欢迎改进文档！请参考：

1. [贡献指南](development/contributing.md) - 了解如何参与
2. 文档使用 Markdown 格式
3. 中文文档放在 `reference/chinese/`
4. 新增重要文档请更新本索引

## 📮 反馈和建议

- 发现文档问题？请提 [Issue](https://github.com/your-repo/issues)
- 有改进建议？欢迎提 [Pull Request](https://github.com/your-repo/pulls)

---

**文档版本**：v1.0  
**最后更新**：2026-01-15  
**维护者**：项目团队
