FROM node:20-alpine AS base

WORKDIR /app
# 构建阶段需要 dev 依赖（TypeScript 等）
ENV NODE_ENV=development

# 可覆盖的 API 地址（用于 Next 编译时注入）
ARG NEXT_PUBLIC_API_BASE=http://localhost:8020
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}

# 安装依赖（包含 dev 依赖以便构建）
COPY package.json package-lock.json ./
RUN npm ci --include=dev

# 复制源代码并构建（生产模式）
COPY . .
ENV NODE_ENV=production
RUN npm run build
# 仅保留生产依赖
RUN npm prune --omit=dev

EXPOSE 3000

CMD ["npm", "run", "start"]
