# RAGForge Frontend

RAGForge 管理界面，基于 Next.js 15 + React 19 + TailwindCSS + shadcn/ui 构建。

## 目录

- [快速开始](#快速开始)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [页面功能](#页面功能)
- [组件开发指南](#组件开发指南)
- [RAG 算法参数](#rag-算法参数)
- [API 交互](#api-交互)
- [模型优先级](#模型优先级)
- [向量存储隔离](#向量存储隔离)
- [测试清单](#测试清单)
- [代码规范](#代码规范)

---

## 快速开始

```bash
# 安装依赖
pnpm install

# 开发模式（端口 3000）
pnpm dev

# 构建
pnpm build

# 生产模式
pnpm start
```

浏览器打开 [http://localhost:3000](http://localhost:3000) 查看。

### 环境变量

```bash
# .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8020
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **框架** | Next.js 15 (App Router) |
| **UI** | TailwindCSS + shadcn/ui + Lucide Icons |
| **状态** | Zustand（全局状态）+ React useState（本地状态）|
| **请求** | fetch API |
| **包管理** | pnpm |

---

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (main)/             # 主布局页面
│   │   │   ├── compare/        # Ground 实验页面
│   │   │   │   ├── page.tsx    # 实验列表
│   │   │   │   └── [id]/page.tsx # 实验详情（分段设置）
│   │   │   ├── knowledge-bases/ # 知识库管理页面
│   │   │   │   ├── page.tsx    # 知识库列表
│   │   │   │   └── [id]/page.tsx # 知识库详情
│   │   │   └── layout.tsx      # 主布局
│   │   ├── globals.css         # 全局样式
│   │   └── layout.tsx          # 根布局
│   ├── components/             # 通用组件
│   │   ├── ui/                 # shadcn/ui 组件
│   │   ├── chat/               # 聊天相关组件
│   │   └── settings/           # 设置相关组件
│   └── lib/
│       ├── store.ts            # Zustand 全局状态管理
│       ├── api.ts              # API 客户端
│       └── utils.ts            # 工具函数
├── public/                     # 静态资源
└── package.json
```

---

## 页面功能

### Ground 实验页面 (`/compare/[id]`)

RAG Pipeline 分段设置与预览页面。

**文档管理**
- 文件上传（仅保存原始内容，不切分）
- 文件列表展示（名称、大小、上传时间）
- 文件删除

**分段设置**
- 切分器选择（9 种切分器）
- 参数动态配置（支持分组、条件显示）
- 分段预览（普通模式/父子分块模式）

**多 Pipeline 管理**
- 最多 4 个独立 Pipeline
- 配置通过 localStorage 持久化
- 支持检索对比联动

**配置变更检测**：修改切分/索引配置后自动提示重新入库。

### 知识库详情页 (`/knowledge-bases/[id]`)

**文件管理** - 文件上传（拖拽、批量）、列表、删除、状态显示

**检索测试** - 查询测试界面

**配置** - 基础信息、图标配置、嵌入模型选择

### 聊天页 (`/chat`)

- 流式响应（SSE）
- Markdown 渲染
- 引用来源展示
- 对话历史持久化

### 设置页 (`/settings`)

- API 配置
- 模型提供商管理
- 默认模型配置
- API Key 管理（admin）

---

## 组件开发指南

### AllModelsSelector（统一模型选择器）

**所有模型选择场景都应使用此组件**：

```typescript
import { AllModelsSelector } from "@/components/settings";

<AllModelsSelector
  type="embedding"  // "llm" | "embedding" | "rerank"
  value={{ provider: "ollama", model: "bge-m3" }}
  onChange={(val) => setModel(val)}
  placeholder="选择模型"
/>
```

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"llm" \| "embedding" \| "rerank"` | 是 | 模型类型 |
| `value` | `{ provider: string; model: string }` | 否 | 当前选中值 |
| `onChange` | `(val) => void` | 是 | 选择回调 |
| `placeholder` | `string` | 否 | 占位文本 |

### 添加新切分器 UI

在 `CHUNKER_UI_CONFIG` 中添加配置：

```typescript
const CHUNKER_UI_CONFIG = {
  my_chunker: {
    label: '我的切分器',
    description: '切分器描述',
    params: [
      { key: 'param1', label: '参数1', type: 'number', default: 100 },
      { key: 'param2', label: '参数2', type: 'boolean', default: true },
      { key: 'param3', label: '参数3', type: 'select', default: 'opt1',
        options: ['opt1', 'opt2'] },
    ]
  },
};
```

**参数类型**：`number` | `boolean` | `select` | `text` | `slider`

---

## RAG 算法参数

### 切分器 (Chunkers)

| 名称 | 说明 | 主要参数 |
|------|------|----------|
| `simple` | 按段落切分 | `max_chars` (800) |
| `sliding_window` | 滑动窗口 | `window` (800), `overlap` (200) |
| `parent_child` | 父子分块 | `parent_chars` (1600), `child_chars` (400) |
| `recursive` | 递归字符切分 **（推荐）** | `chunk_size` (1024), `chunk_overlap` (256) |
| `markdown` | Markdown 感知 | `chunk_size`, `strip_headers` |
| `code` | 代码感知 | `language`, `max_chunk_size`, `include_imports` |
| `llama_sentence` | 句子级切分 | `max_tokens` (512) |
| `llama_token` | Token 级切分 | `max_tokens` (512) |

### 检索器 (Retrievers)

| 名称 | 说明 | 主要参数 |
|------|------|----------|
| `dense` | 稠密向量检索 | - |
| `bm25` | BM25 稀疏检索 | - |
| `hybrid` | 混合检索 **（推荐）** | `dense_weight` (0.7), `sparse_weight` (0.3) |
| `fusion` | RRF 融合 + Rerank | `mode`, `rerank`, `rerank_model` |
| `hyde` | HyDE 假设文档 | `base_retriever`, `num_queries` (4) |
| `multi_query` | 多查询扩展 | `base_retriever`, `num_queries` (3) |
| `parent_document` | 父文档检索 | `base_retriever`, `return_parent` |

### 检索器兼容性

| 检索器 | 要求 |
|--------|------|
| `parent_document` | 需使用 `parent_child` 切分器 |
| `raptor` | 需启用 RAPTOR 索引 |

---

## API 交互

### 知识库 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/knowledge-bases` | GET/POST | 列表/创建 |
| `/v1/knowledge-bases/{id}` | PATCH/DELETE | 更新/删除 |
| `/v1/knowledge-bases/{id}/documents` | GET | 文档列表 |
| `/v1/knowledge-bases/{id}/upload` | POST | 上传文档 |

### Ground 实验 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/ground/{id}/documents` | GET | 获取文档列表 |
| `/ground/{id}/upload` | POST | 上传文档 |
| `/ground/{id}/preview-chunks` | POST | 预览分块结果 |
| `/pipeline/chunkers` | GET | 获取可用切分器 |

### 对话 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/conversations` | GET/POST | 列表/创建 |
| `/v1/conversations/{id}` | GET/DELETE | 详情/删除 |
| `/v1/conversations/{id}/messages` | POST | 添加消息 |
| `/v1/rag/stream` | POST | SSE 流式 RAG |

---

## 模型优先级

### LLM 模型
| 优先级 | 来源 |
|--------|------|
| 1 | 前端默认设置 |
| 2 | 后端环境变量 |

### Embedding 模型
| 优先级 | 来源 |
|--------|------|
| 1 | 知识库配置 |
| 2 | 前端默认设置 |
| 3 | 后端环境变量 |

> **注意**：Embedding 模型在检索时无法动态切换，必须使用入库时的配置。

### Rerank 模型
| 优先级 | 来源 |
|--------|------|
| 1 | 检索组件选择 |
| 2 | 前端默认设置 |
| 3 | 后端环境变量 |

---

## 向量存储隔离

| 模式 | Collection 名称 | 适用场景 |
|------|----------------|---------|
| **Partition** | `kb_shared` | 小规模、资源共享（推荐）|
| **Collection** | `kb_{tenant_id}` | 大规模、高性能需求 |
| **Auto** | 自动选择 | 自动优化 |

**配置存储**：`localStorage` (key: `vector_isolation_mode`)

> **注意**：切换模式不会自动迁移已有数据，入库和检索必须使用相同模式。

---

## 测试清单

### 基础布局
- [ ] 侧边栏折叠/展开
- [ ] 移动端菜单
- [ ] 主题切换（深色/浅色）
- [ ] 导航跳转

### 设置页 `/settings`
- [ ] API Base 配置
- [ ] API Key 配置
- [ ] 连接测试
- [ ] API Key 管理（admin）

### 聊天页 `/chat`
- [ ] 发送消息
- [ ] 流式响应
- [ ] Markdown 渲染
- [ ] 来源引用展示
- [ ] 对话历史

### 知识库管理 `/knowledge-bases`
- [ ] 知识库列表
- [ ] 创建/删除知识库
- [ ] 文件上传
- [ ] 文档管理

---

## 代码规范

- **组件**: 函数组件 + Hooks
- **样式**: TailwindCSS utility classes
- **类型**: TypeScript 严格模式
- **命名**: 组件 PascalCase，文件 kebab-case

### 设计规范（基于 Ant Design）

- **间距**: 8px 倍数
- **圆角**: 4px / 8px / 16px
- **色彩**: CSS 变量
- **动效**: 100ms / 200ms / 300ms

---

## 相关文件

- `src/lib/store.ts` - 全局状态管理
- `src/lib/api.ts` - API 客户端
- `src/components/settings/` - 设置相关组件
- `src/app/(main)/compare/[id]/page.tsx` - Ground 实验页面

详细开发文档请参考 [AGENTS.md](./AGENTS.md)。
