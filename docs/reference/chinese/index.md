# 中文参考文档

这里汇总了项目中所有的中文文档，方便中文开发者查阅。

## 📚 核心文档

- **[API 设计说明](./api-design)** - 详细的接口定义和参数说明
- **[开发指南](./development)** - 详细的中文开发指南
- **[优化指南](./optimization)** - 性能优化和算法调优
- **[实践总结](./practice-summary)** - 项目实践经验总结

**为什么保留中文内容？**
虽然项目主要文档采用英文（为了国际化），但考虑到团队成员和部分用户的语言习惯，我们保留并持续维护这部分中文核心文档，特别是涉及复杂业务逻辑和最佳实践的部分。

## 📖 详细列表

### 1. 开发与架构

#### [API 设计说明 (api-design.md)](./api-design)
**原始文件**：`docs/API设计.md`

**内容概述**：
- 核心 API 路由定义
- 请求/响应模型结构
- 错误码规范

#### [开发指南 (development.md)](./development)
**原始文件**：`docs/开发.md`

**内容概述**：
- 环境搭建与配置
- 核心模块开发流程
- 调试技巧

#### [多租户开发指南 (tenant-development.md)](./tenant-development)
**原始文件**：`docs/租户开发.md`

**内容概述**：
- 租户隔离策略
- 数据模型设计
- 权限控制实现

### 2. 测试与优化

#### [优化指南 (optimization.md)](./optimization)
**原始文件**：`docs/优化.md`

**内容概述**：
- 向量检索性能优化
- 数据库查询优化
- 系统并发能力提升

#### [测试记录 (test-records.md)](./test-records)
**原始文件**：`docs/测试记录.md`

**内容概述**：
- 性能测试基准
- 压力测试结果
- 优化前后对比

#### [OpenAI SDK 测试总结 (openai-sdk-testing.md)](../../reports/openai-sdk-testing.md)
**原始文件**：`docs/OpenAI接口和SDK测试总结.md`

**内容概述**：
- 兼容性测试报告
- 已知问题与规避方案

### 3. 部署与运维

#### [部署指南 (deployment.md)](./deployment)
**原始文件**：`docs/部署.md`

**内容概述**：
- Docker Compose 部署
- 生产环境配置建议
- 常见问题排查

#### [向量维度修复 (vector-dimension-fix.md)](./vector-dimension-fix)
**原始文件**：`docs/向量维度修复.md`

**内容概述**：
- 维度不匹配问题的排查
- 修复脚本的使用
- 预防措施

### 📚 按主题浏览
- **开发相关** → [开发指南](./development)
- **性能优化** → [优化指南](./optimization)
- **实践经验** → [实践总结](./practice-summary)
- **多租户** → [多租户开发](./tenant-development)

### 🔍 按难度浏览
- **入门级** → [实践总结](./practice-summary)
- **进阶级** → [开发指南](./development) + [优化指南](./optimization)
- **专家级** → [多租户开发](./tenant-development) + [向量维度修复](./vector-dimension-fix)

### 🎯 按用途浏览
- **学习开发** → [开发指南](./development)
- **解决问题** → [向量维度修复](./vector-dimension-fix)
- **性能调优** → [优化指南](./optimization)
- **项目实施** → [实践总结](./practice-summary)
