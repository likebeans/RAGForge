---
layout: home

hero:
  name: "Self-RAG Pipeline"
  text: "多租户知识库检索服务"
  tagline: "Multi-tenant Knowledge Base Retrieval Service with OpenAI-compatible API"
  image:
    src: /logo.svg
    alt: Self-RAG Pipeline
  actions:
    - theme: brand
      text: 快速开始
      link: /getting-started/
    - theme: alt
      text: 查看文档
      link: /documentation
    - theme: alt
      text: 查看 GitHub
      link: https://github.com/your-org/self-rag-pipeline

features:
  - icon: 🏢
    title: 多租户架构
    details: 完整的多租户支持，包括租户隔离、配额管理和权限控制，适合企业级部署
  
  - icon: 🔌
    title: OpenAI 兼容接口
    details: 提供完全兼容 OpenAI API 的接口，支持 Chat Completions 和 Embeddings，无缝集成现有应用
  
  - icon: 🧠
    title: 先进检索算法
    details: 支持稠密检索、BM25、混合检索、RAPTOR 等多种算法，可根据场景灵活选择
  
  - icon: 🔄
    title: 可插拔架构
    details: 模块化设计，支持自定义切分器、检索器、增强器等组件，易于扩展和定制
  
  - icon: 🌐
    title: 多 LLM 提供商
    details: 支持 OpenAI、Ollama、Qwen、智谱 AI 等多种 LLM 提供商，灵活选择最适合的模型
  
  - icon: 📊
    title: 完整可观测性
    details: 内置结构化日志、请求追踪、审计日志和性能监控，便于运维和问题排查
  
  - icon: 🐍
    title: Python SDK
    details: 提供完整的 Python SDK，支持知识库管理、文档上传、检索和 RAG 生成等所有功能
  
  - icon: 🚀
    title: 生产就绪
    details: 支持 Docker 部署、数据库迁移、配置管理等生产环境必需功能，开箱即用
---

## 快速了解

Self-RAG Pipeline 是一个企业级的多租户知识库检索服务，专为需要大规模部署 RAG（检索增强生成）应用的组织设计。

### 核心特性

- **🏢 多租户支持**：完整的租户隔离和管理，支持不同的向量存储隔离策略
- **🔌 标准接口**：OpenAI 兼容的 API 接口，无需修改现有代码即可集成
- **🧠 智能检索**：支持多种检索算法，包括最新的 RAPTOR 多层次索引
- **🔄 灵活扩展**：可插拔的算法框架，支持自定义组件开发
- **📊 企业级**：完整的监控、日志、审计和安全功能

### 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端应用      │    │   Python SDK    │    │   第三方应用    │
│   (Next.js)     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   FastAPI 服务  │
                    │  (OpenAI 兼容)  │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   LLM 提供商    │
│ (元数据+向量)   │    │   (缓存+限流)   │    │ (OpenAI/Ollama) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 开始使用

1. **[安装部署](/getting-started/installation)** - 快速部署和配置指南
2. **[快速开始](/getting-started/quick-start)** - 5 分钟上手教程
3. **[使用指南](/guides/)** - 详细的使用指南和最佳实践
4. **[API 文档](/architecture/api-specification)** - 完整的 API 参考
5. **[Python SDK](/sdk/)** - SDK 使用指南

### 文档导航

- 📖 **[完整文档索引](/documentation)** - 查看所有文档
- 🏗️ **[架构设计](/architecture/)** - 系统架构和设计文档
- 👨‍💻 **[开发文档](/development/)** - 开发者指南
- 🔧 **[运维文档](/operations/)** - 部署和运维指南
- 📊 **[报告总结](/reports/)** - 项目报告和历史记录

### 社区与支持

- 📖 **文档**：完整的中英文文档，涵盖安装、开发、部署等各个方面
- 🐛 **问题反馈**：通过 GitHub Issues 报告问题和建议
- 💬 **讨论交流**：加入我们的社区讨论技术问题和最佳实践
- 🤝 **贡献代码**：欢迎提交 Pull Request 参与项目开发

---

<div style="text-align: center; margin-top: 2rem; padding: 1rem; background: var(--vp-c-bg-soft); border-radius: 8px;">
  <p><strong>🚀 准备开始了吗？</strong></p>
  <p>从 <a href="/getting-started/">入门指南</a> 开始，或者直接查看 <a href="/getting-started/quick-start">快速开始</a> 教程。</p>
  <p>查看 <a href="/documentation">完整文档索引</a> 了解更多内容。</p>
</div>
