# Yaoyan AI 平台

面向企业知识管理与问答的全栈项目，提供用户/角色/部门/项目管理、RAGForge 代理、PDF 智能提取等能力。

- 后端：FastAPI + SQLAlchemy + Alembic（Python 3.12）
- 前端：React 18 + Vite + TailwindCSS
- 部署：Dockerfile + docker-compose（前端容器内 nginx 反代 /api 到后端）
- 数据库：PostgreSQL（可复用 RAGForge 的数据库实例）

## 目录结构
```
yaoyan_AI/
├─ backend/
│  ├─ app/            FastAPI 应用（路由、模型、服务、Schema）
│  ├─ alembic/        数据库迁移脚本
│  ├─ Dockerfile      后端镜像
│  ├─ entrypoint.sh   容器启动脚本（等待数据库 → 迁移 → 启动）
│  └─ .env.example    后端环境变量示例
├─ src/               前端源码（React）
├─ Dockerfile.frontend  前端镜像（nginx 托管静态资源并代理 /api）
├─ docker-compose.yml   一体化编排
├─ .env.example         根目录环境变量示例（compose 使用）
└─ nginx.conf           前端容器内 nginx 配置
```

## 快速开始（Docker Compose）
1. 复制根目录 `.env.example` 为 `.env`，并按环境修改关键项：
   - 数据库：`DATABASE_URL`、`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`
   - 安全：`JWT_SECRET_KEY`、`API_KEY_ENCRYPTION_KEY`（生产务必更换强密钥）
   - RAGForge：`RAGFORGE_BASE_URL`、`RAGFORGE_ADMIN_KEY`
   - 端口：`BACKEND_PORT`（默认 3002）、`FRONTEND_PORT`（默认 5173）
2. 一键启动
```bash
docker compose up -d --build
```
3. 服务访问
   - 前端：http://localhost:5173
   - 后端健康检查：http://localhost:3002/health
   - 后端 API 文档（Swagger）：http://localhost:3002/docs

说明：前端容器内 nginx 已将 `/api/*` 代理到 `yaoyan-backend:3002/api/*`，无需在前端手动配置后端地址。

## 本地开发
### 后端（FastAPI）
使用 uv 安装依赖并启动：
```bash
pip install uv
uv pip install -e .
cp backend/.env.example backend/.env
uvicorn app.main:app --reload --port 3002
```
数据库迁移：
```bash
cd backend
alembic upgrade head
```

### 前端（React + Vite）
```bash
npm ci
npm run dev
```
开发模式下，前端默认以相对路径访问 `/api`。如果不使用 docker-compose，可在 Vite 开发服务器增加代理到本地后端：
```js
// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:3002', changeOrigin: true },
    },
  },
})
```

## 环境变量
- 根目录与 `backend/` 均提供 `.env.example`，请复制为 `.env` 并按环境修改。
- 不要在仓库中提交真实密钥或访问令牌；生产环境通过安全方式注入。

## 功能概览
- 认证与用户管理：注册/登录、用户信息、角色与部门关联
- 项目管理：增删改查、批量导入导出、模板下载
- 字典管理：按分类查询
- RAGForge 代理：知识库、文档上传、检索与 RAG 生成、流式输出
- PDF 智能提取：定义提取 Schema，批量抽取并输出 JSON/Excel

## 常见问题
- 无法连通数据库：确认 `DATABASE_URL` 正确；在 Docker 下可用 `host.docker.internal`
- 跨域：确保后端 `CORS_ORIGINS` 包含前端访问源（如 `http://localhost:5173`）
- 上传限制：`nginx.conf` 中已将 `client_max_body_size` 设置为 50M，可按需调整

## 许可
如需开源，请在根目录添加 LICENSE 文件；未指定时默认保留所有权利。
