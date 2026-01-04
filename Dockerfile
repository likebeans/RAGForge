# 使用官方 uv 镜像作为构建基础
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

## 可选：构建阶段代理（仅 build 使用，运行时会清空）
ARG BUILD_HTTP_PROXY
ENV http_proxy=${BUILD_HTTP_PROXY} \
    https_proxy=${BUILD_HTTP_PROXY}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=120

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存
COPY pyproject.toml uv.lock ./

# 安装依赖（不安装项目本身）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# 复制源代码
COPY app ./app
COPY main.py alembic.ini README.md ./
COPY alembic ./alembic
COPY sdk ./sdk
COPY scripts ./scripts
RUN chmod +x ./scripts/docker-entrypoint.sh

# 安装项目
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# 运行时清空代理，避免生产环境意外走代理
ENV http_proxy= \
    https_proxy= \
    HTTP_PROXY= \
    HTTPS_PROXY=

EXPOSE 8020

# 使用启动脚本（包含健康检查预热）
CMD ["./scripts/docker-entrypoint.sh"]
