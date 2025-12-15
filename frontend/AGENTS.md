# Frontend 前端模块

RAG Pipeline 的管理界面，基于 Next.js 15 + React 19 + TailwindCSS + shadcn/ui 构建。

## 技术栈

- **框架**: Next.js 15 (App Router)
- **UI**: TailwindCSS + shadcn/ui + Lucide Icons
- **状态**: Zustand（全局状态） + React useState（本地状态）
- **请求**: fetch API
- **包管理**: pnpm

## 开发环境

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
│   │   │   │   └── [id]/page.tsx # 知识库详情（文件管理、配置）
│   │   │   └── layout.tsx      # 主布局
│   │   ├── globals.css         # 全局样式
│   │   └── layout.tsx          # 根布局
│   ├── components/             # 通用组件
│   │   ├── ui/                 # shadcn/ui 组件
│   │   ├── chat/               # 聊天相关组件
│   │   ├── settings/           # 设置相关组件
│   │   │   ├── all-models-selector.tsx  # 全局模型选择器
│   │   │   ├── model-selector.tsx       # 单提供商模型选择器
│   │   │   ├── model-provider-config.tsx # 模型提供商配置
│   │   │   └── default-model-config.tsx  # 默认模型配置
│   │   └── provider-model-selector.tsx # 旧版模型选择器（兼容）
│   └── lib/
│       ├── store.ts            # Zustand 全局状态管理
│       ├── api.ts              # API 客户端
│       └── utils.ts            # 工具函数
├── public/                     # 静态资源
└── package.json
```

## 页面功能

### Ground 实验页面 (`/compare/[id]`)

RAG Pipeline 分段设置与预览页面，核心功能：

**文档管理**
- 文件上传（仅保存原始内容，不切分）
- 文件列表展示（名称、大小、上传时间）
- 文件删除

**分段设置**
- 切分器选择（9 种切分器）
- 参数动态配置（支持分组、条件显示）
- 分段预览（普通模式/父子分块模式）

**支持的切分器**

| 切分器 | 说明 | 主要参数 |
|--------|------|---------|
| `simple` | 简单分段 | separator, max_chars |
| `sliding_window` | 滑动窗口 | window, overlap |
| `parent_child` | 父子分块 | parent_mode, separators, max_chars |
| `recursive` | 递归字符 | chunk_size, separators, keep_separator |
| `markdown` | Markdown | headers_to_split_on, strip_headers |
| `code` | 代码感知 | language, include_imports |
| `llama_sentence` | 句子级 | max_tokens |
| `llama_token` | Token级 | max_tokens |

**参数类型**
- `number`: 数字输入框
- `boolean`: 开关
- `select`: 下拉选择
- `text`: 文本输入（支持分隔符自定义）
- `slider`: 滑块

**预览模式**
- 普通分块：显示每个 chunk 的文本和元数据
- 父子分块：按父块分组，子块高亮显示

### 知识库详情页面 (`/knowledge-bases/[id]`)

知识库管理页面，包含以下导航标签：

**文件管理** (`files`)
- 文件上传（支持拖拽、批量上传）
- 文件列表（名称、上传时间、分块数、状态）
- 文件删除
- 解析状态显示

**检索测试** (`search`)
- 查询测试界面

**日志** (`logs`)
- 操作日志记录

**配置** (`config`)
- 知识库基础信息（名称、描述）
- 知识库图标配置（预设图标选择、自定义图片上传）
- 嵌入模型配置（使用 AllModelsSelector 选择）

**图标配置功能**
- 支持 8 种预设图标（Database、BookOpen、Sparkles、Brain、Lightbulb、ScrollText、GraduationCap、Archive）
- 支持自定义图片上传（JPG、PNG、GIF，最大 2MB）
- 图标存储在 localStorage（`kb_covers` 和 `kb_custom_icons`）

### 模型选择组件

#### AllModelsSelector（统一组件）

**所有需要选择模型的场景都应该使用此组件**，包括：
- 知识库配置页的 Embedding 模型选择
- Ground 实验页的 Embedding 模型选择
- Ground 实验页的 LLM 模型选择
- 任何其他需要选择 LLM / Embedding / Rerank 模型的场景

```typescript
import { AllModelsSelector } from "@/components/settings";

<AllModelsSelector
  type="embedding"  // "llm" | "embedding" | "rerank"
  value={{ provider: "ollama", model: "bge-m3" }}
  onChange={(val) => setModel(val)}
  placeholder="选择模型"
/>
```

**Props**：
| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"llm" \| "embedding" \| "rerank"` | 是 | 模型类型 |
| `value` | `{ provider: string; model: string } \| undefined` | 否 | 当前选中值 |
| `onChange` | `(val: { provider: string; model: string } \| null) => void` | 是 | 选择回调 |
| `placeholder` | `string` | 否 | 占位文本 |
| `label` | `string` | 否 | 标签文本 |
| `disabled` | `boolean` | 否 | 禁用状态 |

**特性**：
- 按提供商分组显示所有可用模型
- 支持搜索过滤（按模型名或提供商名）
- 显示提供商图标和验证状态
- 无可用模型时显示配置链接
- 自动从全局状态读取已验证的提供商列表

## API 交互

前端通过以下端点与后端交互：

### Ground 实验 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/ground/{id}/documents` | GET | 获取文档列表 |
| `/ground/{id}/upload` | POST | 上传文档 |
| `/ground/{id}/documents/{doc_id}` | DELETE | 删除文档 |
| `/ground/{id}/preview-chunks` | POST | 预览分块结果 |
| `/pipeline/chunkers` | GET | 获取可用切分器 |

### 知识库 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/knowledge-bases` | GET | 获取知识库列表 |
| `/v1/knowledge-bases` | POST | 创建知识库 |
| `/v1/knowledge-bases/{id}` | PATCH | 更新知识库（名称、描述、配置） |
| `/v1/knowledge-bases/{id}` | DELETE | 删除知识库 |
| `/v1/knowledge-bases/{id}/documents` | GET | 获取知识库文档列表 |
| `/v1/knowledge-bases/{id}/upload` | POST | 上传文档到知识库 |

## 组件开发指南

### 添加新切分器 UI

在 `compare/[id]/page.tsx` 的 `CHUNKER_UI_CONFIG` 中添加配置：

```typescript
const CHUNKER_UI_CONFIG: Record<string, ChunkerConfig> = {
  my_chunker: {
    label: '我的切分器',
    description: '切分器描述',
    params: [
      { key: 'param1', label: '参数1', type: 'number', default: 100 },
      { key: 'param2', label: '参数2', type: 'text', default: '\\n' },
      { key: 'param3', label: '参数3', type: 'boolean', default: true },
      { key: 'param4', label: '参数4', type: 'select', default: 'opt1',
        options: ['opt1', 'opt2'] },
    ]
  },
};
```

### 参数分组与条件显示

```typescript
{
  key: 'advanced_param',
  label: '高级参数',
  type: 'number',
  default: 100,
  group: '高级设置',           // 分组名称
  showWhen: { mode: 'advanced' } // 条件显示
}
```

## 环境变量

```bash
# .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8020
```

## 模型优先级逻辑

前端使用模型时遵循以下优先级规则（从高到低）：

### LLM 模型

用于 HyDE/MultiQuery 检索器生成假设答案：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 前端默认设置 | 设置页面配置的默认 LLM |
| 2 | 后端 env | 未配置时回退到后端环境变量 |

### Rerank 模型

用于检索结果重排序：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 检索组件选择 | 检索对比页面单独选择的 Rerank 模型 |
| 2 | 前端默认设置 | 设置页面配置的默认 Rerank |
| 3 | 后端 env | 未配置时回退到后端环境变量 |

### Embedding 模型

用于文档入库时的向量化：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 知识库配置 | 知识库配置页面选择的 Embedding 模型 |
| 2 | 前端默认设置 | 未选择时自动使用设置页面的默认 Embedding |
| 3 | 后端 env | 未配置时回退到后端环境变量 |

**注意**：Embedding 模型在检索时无法动态切换，必须使用知识库入库时的配置，否则向量空间不匹配会导致检索结果错误。

## 向量存储隔离模式

设置页面的 **向量存储** Tab 提供多租户隔离策略配置。

### 隔离模式

| 模式 | Collection 名称 | 隔离方式 | 适用场景 |
|------|----------------|---------|---------|
| **Partition** | `kb_shared` | 通过 `kb_id` 字段过滤 | 小规模、资源共享（推荐） |
| **Collection** | `kb_{tenant_id}` | 每租户独立 Collection | 大规模、高性能需求 |
| **Auto** | 自动选择 | 根据数据量自动切换 | 自动优化、平衡成本 |

### 配置存储

- **存储位置**：`localStorage`（key: `vector_isolation_mode`）
- **默认值**：`partition`

### 注意事项

1. **切换模式不会自动迁移已有数据**
2. 如果已有数据使用 Partition 模式入库，请保持使用该模式
3. 入库和检索必须使用相同的隔离模式，否则检索将无法找到数据

### 技术实现

- 入库服务（`ingestion.py`）：调用 `vector_store.upsert_chunks()` 时根据策略选择 Collection
- 检索器（如 `llama_dense.py`）：需与入库时使用的 Collection 名称一致
- 前端配置仅作为显示和提醒，实际隔离策略由后端 `config.py` 环境变量控制

## 代码规范

- **组件**: 函数组件 + Hooks
- **样式**: TailwindCSS utility classes
- **类型**: TypeScript 严格模式
- **命名**: 组件 PascalCase，文件 kebab-case
