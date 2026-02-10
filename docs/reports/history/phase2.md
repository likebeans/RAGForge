# Phase 2: 高级特性与生态完善

## 目标
增强检索效果，支持更多模型和数据源，提升系统易用性。

## 任务列表

### 1. 检索增强
- [x] 实现混合检索 (Hybrid Search: Dense + BM25)
- [x] 引入 Rerank 机制 (Cohere/BGE-Reranker)
- [x] 开发多查询 (Multi-Query) 和 HyDE 策略

### 2. 算法扩展
- [x] 实现 RAPTOR 索引机制
- [x] 添加父子文档检索 (Parent-Child)
- [x] 增加 Markdown 和 Code 专用切分器

### 3. 模型生态
- [x] 支持更多 LLM 提供商 (Zhipu, Moonshot, DeepSeek)
- [x] 实现模型配置的热加载与租户级覆盖

### 4. SDK 与工具
- [x] 开发 Python SDK
- [x] 提供 OpenAI 兼容接口
- [x] 编写 Docker Compose 部署脚本

## 成果
系统具备了高级 RAG 能力，支持多种检索策略和模型组合，生态初步完善。
