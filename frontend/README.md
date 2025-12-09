# RAG Pipeline Frontend

RAG Pipeline 管理界面，用于配置和测试文档切分、检索等功能。

## 快速开始

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

浏览器打开 [http://localhost:3000](http://localhost:3000) 查看。

## 功能模块

### Ground 实验页面 (`/compare`)

文档切分设置与预览：

- **文档管理**：上传、列表、删除
- **切分器配置**：9 种切分器，参数动态配置
- **分块预览**：普通模式 / 父子分块模式
- **元数据展示**：显示切分器输出的元数据

### 支持的切分器

| 切分器 | 说明 |
|--------|------|
| 简单分段 | 按自定义分隔符切分 |
| 滑动窗口 | 固定窗口 + 重叠 |
| 父子分块 | 子块检索 + 父块上下文 |
| 递归字符 | 优先保持语义边界 |
| Markdown | 按标题层级分块 |
| 代码感知 | 按语法结构分块 |

## 技术栈

- **Next.js 15** - React 框架
- **TailwindCSS** - 样式
- **shadcn/ui** - UI 组件库
- **TypeScript** - 类型安全

## 环境变量

```bash
# .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8020
```

## 项目结构

```
src/
├── app/                    # 页面
│   └── (main)/compare/     # Ground 实验页面
├── components/             # 组件
│   ├── ui/                 # shadcn/ui
│   └── chat/               # 聊天组件
└── lib/                    # 工具函数
```

## 开发

```bash
pnpm dev      # 开发模式
pnpm build    # 构建
pnpm start    # 生产模式
pnpm lint     # 代码检查
```

## 文档

详细开发文档请参考 [AGENTS.md](./AGENTS.md)。
