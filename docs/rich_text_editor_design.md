# 富文本编辑器与草稿箱功能技术设计文档

## 1. 概述
本设计文档旨在说明“新建报告”页面中集成的富文本编辑器及草稿箱功能的技术实现方案。该功能允许用户编写格式化报告内容，支持自动保存草稿、手动保存草稿及正式发布，并提供草稿管理功能。

## 2. 架构设计

### 2.1 前端架构
前端基于 React 框架，利用 `react-quill` 实现富文本编辑功能。
- **组件结构**：
  - `ReportNew` (页面容器)：负责整体布局，状态协调（当前草稿加载、列表刷新）。
  - `ReportEditor` (核心组件)：封装 `ReactQuill`，实现内容编辑、自动保存定时器、手动保存逻辑。
  - `DraftList` (辅助组件)：展示草稿列表，支持加载和删除草稿。
- **服务层**：
  - `reportService`：封装与后端 `reports` API 的通信逻辑。

### 2.2 后端架构
后端基于 FastAPI + SQLAlchemy (Async)，新增 `reports` 模块。
- **数据模型** (`Report`)：存储报告标题、内容、状态（草稿/已发布）、关联用户及时间戳。
- **API 接口**：遵循 RESTful 规范，提供 CRUD 操作。

## 3. 接口定义

### 3.1 报告管理 API (`/api/reports`)

| 方法 | 路径 | 描述 | 参数 |
|---|---|---|---|
| POST | `/` | 创建报告 | `title`, `content`, `status` |
| GET | `/` | 获取报告列表 | `status` (可选), `skip`, `limit` |
| GET | `/{id}` | 获取单个报告 | `id` |
| PUT | `/{id}` | 更新报告 | `title`, `content`, `status` |
| DELETE | `/{id}` | 删除报告 | `id` |

## 4. 关键实现细节

### 4.1 自动保存
- **前端实现**：`ReportEditor` 组件内部维护一个定时器（默认 30 秒）。每隔一段时间检查内容或标题是否发生变化（通过 `useRef` 记录上次保存状态）。如果变化且非空，则调用 `saveReport('draft')` 接口。
- **触发条件**：内容变更且非空。

### 4.2 草稿与正式报告分离
- **状态区分**：通过数据库字段 `status` ('draft' vs 'published') 区分。
- **存储**：统一存储在 `reports` 表中，便于后续将草稿转为正式报告（仅需更新状态）。
- **展示**：`DraftList` 组件仅请求 `status=draft` 的记录。

### 4.3 数据持久化
- **数据库**：使用 SQLite (开发环境) 或 PostgreSQL (生产环境)。
- **迁移**：通过 Alembic 脚本 `ffcd18cedb60_create_report_content_table.py` 创建 `reports` 表。

## 5. 部署说明
1. **数据库迁移**：运行 `alembic upgrade head` 应用数据库变更。
2. **前端构建**：无需额外配置，确保 `react-quill` 依赖已安装。

