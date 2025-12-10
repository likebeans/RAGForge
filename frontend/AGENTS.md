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

#### AllModelsSelector（推荐）

全局模型选择器，聚合所有已验证提供商的可用模型：

```typescript
import { AllModelsSelector } from "@/components/settings";

<AllModelsSelector
  type="embedding"  // "llm" | "embedding" | "rerank"
  value={{ provider: "ollama", model: "bge-m3" }}
  onChange={(val) => setModel(val)}
  label="嵌入模型"
  placeholder="选择模型"
/>
```

**特性**：
- 按提供商分组显示所有可用模型
- 支持搜索过滤（按模型名或提供商名）
- 显示提供商图标和验证状态
- 无可用模型时显示配置链接

#### ProviderModelSelector（旧版）

单提供商模型选择器，需先选择提供商再选择模型：

```typescript
import { ProviderModelSelector } from "@/components/settings";

<ProviderModelSelector
  type="embedding"
  value={{ provider: "ollama", model: "bge-m3" }}
  onChange={(provider, model) => setModel({ provider, model })}
/>
```

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

## 代码规范

- **组件**: 函数组件 + Hooks
- **样式**: TailwindCSS utility classes
- **类型**: TypeScript 严格模式
- **命名**: 组件 PascalCase，文件 kebab-case
