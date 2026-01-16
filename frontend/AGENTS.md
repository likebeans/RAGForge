# RAGForge Frontend - AI 开发指南

本文档为 AI 编程助手提供前端模块的开发上下文和指南。

> 完整文档请参考 [README.md](./README.md)

---

## 项目概述

RAGForge 前端管理界面，基于 **Next.js 15 + React 19 + TailwindCSS + shadcn/ui** 构建。

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 15 (App Router) |
| UI | TailwindCSS + shadcn/ui + Lucide Icons |
| 状态 | Zustand（全局）+ useState（本地）|
| 请求 | fetch API |
| 包管理 | pnpm |

## 快速命令

```bash
pnpm install   # 安装依赖
pnpm dev       # 开发模式 (端口 3000)
pnpm build     # 构建
pnpm start     # 生产模式
```

---

## 核心文件

| 文件 | 说明 |
|------|------|
| `src/lib/store.ts` | Zustand 全局状态管理 |
| `src/lib/api.ts` | API 客户端封装 |
| `src/components/settings/all-models-selector.tsx` | 统一模型选择器 |
| `src/app/(main)/compare/[id]/page.tsx` | Ground 实验页面 |
| `src/app/(main)/knowledge-bases/[id]/page.tsx` | 知识库详情页面 |

---

## 开发规范

### 代码风格

- **组件**: 函数组件 + Hooks
- **样式**: TailwindCSS utility classes
- **类型**: TypeScript 严格模式
- **命名**: 组件 PascalCase，文件 kebab-case

### 设计规范（Ant Design）

- **间距**: 8px 倍数
- **圆角**: 4px / 8px / 16px
- **动效**: 100ms / 200ms / 300ms

---

## 关键组件

### AllModelsSelector

**所有模型选择场景必须使用此组件**：

```typescript
import { AllModelsSelector } from "@/components/settings";

<AllModelsSelector
  type="embedding"  // "llm" | "embedding" | "rerank"
  value={{ provider: "ollama", model: "bge-m3" }}
  onChange={(val) => setModel(val)}
/>
```

### 添加新切分器

在 `CHUNKER_UI_CONFIG` 中添加：

```typescript
const CHUNKER_UI_CONFIG = {
  my_chunker: {
    label: '切分器名称',
    description: '描述',
    params: [
      { key: 'param1', label: '参数', type: 'number', default: 100 },
    ]
  },
};
```

**参数类型**: `number` | `boolean` | `select` | `text` | `slider`

---

## API 端点

### 知识库

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/knowledge-bases` | GET/POST | 列表/创建 |
| `/v1/knowledge-bases/{id}` | PATCH/DELETE | 更新/删除 |
| `/v1/knowledge-bases/{id}/documents` | GET | 文档列表 |
| `/v1/knowledge-bases/{id}/upload` | POST | 上传文档 |

### Ground 实验

| 端点 | 方法 | 说明 |
|------|------|------|
| `/ground/{id}/documents` | GET | 文档列表 |
| `/ground/{id}/upload` | POST | 上传文档 |
| `/ground/{id}/preview-chunks` | POST | 预览分块 |

### 对话

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/conversations` | GET/POST | 列表/创建 |
| `/v1/conversations/{id}/messages` | POST | 添加消息 |
| `/v1/rag/stream` | POST | SSE 流式 RAG |

---

## 模型优先级

| 模型类型 | 优先级（高→低）|
|----------|---------------|
| **Embedding** | 知识库配置 → 前端默认 → 后端 env |
| **LLM** | 前端默认 → 后端 env |
| **Rerank** | 检索组件选择 → 前端默认 → 后端 env |

> ⚠️ Embedding 模型入库后无法切换，检索必须使用入库时的模型。

---

## 状态持久化

| Key | 存储位置 | 说明 |
|-----|----------|------|
| `ground_pipelines_${id}` | localStorage | Pipeline 配置 |
| `ground-settings-${id}` | localStorage | Ground 设置 |
| `kb_covers` | localStorage | 知识库图标 |
| `vector_isolation_mode` | localStorage | 向量隔离模式 |

---

## 常见任务

### 添加新页面

1. 在 `src/app/(main)/` 下创建目录和 `page.tsx`
2. 使用 shadcn/ui 组件构建 UI
3. 使用 `useAppStore()` 获取全局状态
4. 使用 `client` 调用 API

### 添加新 API 方法

在 `src/lib/api.ts` 的 `RAGClient` 类中添加：

```typescript
async myNewMethod(params: MyParams): Promise<MyResponse> {
  return this.request("POST", "/v1/my-endpoint", params);
}
```

### 添加全局状态

在 `src/lib/store.ts` 中扩展：

```typescript
interface AppState {
  myState: MyType;
  setMyState: (val: MyType) => void;
}

export const useAppStore = create<AppState>((set) => ({
  myState: defaultValue,
  setMyState: (val) => set({ myState: val }),
}));
```

---

## 环境变量

```bash
# .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8020
```
