"""
FastAPI 应用实例

这是 FastAPI 应用的核心配置文件，负责：
1. 创建 FastAPI 应用实例
2. 配置应用生命周期（启动/关闭时的初始化逻辑）
3. 注册所有 API 路由
4. 配置结构化日志和请求追踪
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import update

from app.api.routes import api_router
from app.config import get_settings
from app.db.session import init_models, SessionLocal
from app.infra.logging import setup_logging, get_logger
from app.middleware import RequestTraceMiddleware
from app.middleware.audit import AuditLogMiddleware
from app.models.document import Document

# 配置结构化日志
setup_logging()
logger = get_logger(__name__)

# 获取全局配置（单例模式，整个应用共享同一个配置实例）
settings = get_settings()


async def _mark_interrupted_documents():
    """
    检测并标记卡住的文档
    
    服务重启时，状态为 processing 或 pending 的文档可能是被中断的任务。
    将它们标记为 interrupted，避免前端一直显示"处理中"。
    """
    try:
        async with SessionLocal() as session:
            # 将所有 processing 状态的文档标记为 interrupted
            result = await session.execute(
                update(Document)
                .where(Document.processing_status.in_(["processing", "pending"]))
                .values(processing_status="interrupted")
            )
            await session.commit()
            
            if result.rowcount > 0:
                logger.warning(f"检测到 {result.rowcount} 个中断的文档处理任务，已标记为 interrupted")
    except Exception as e:
        # 如果表还不存在（第一次启动），忽略错误
        logger.debug(f"检测中断文档时出错（可能是首次启动）: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    
    使用 Python 的异步上下文管理器来管理应用的启动和关闭逻辑：
    - yield 之前的代码：应用启动时执行（初始化数据库、连接池等）
    - yield 之后的代码：应用关闭时执行（清理资源、关闭连接等）
    
    注意：
        - 开发环境：使用 init_models() 自动创建表
        - 生产环境：应该使用 Alembic 进行数据库迁移
    """
    # ========== 启动时执行 ==========
    logger.info(f"应用启动中... 环境: {settings.environment}")
    
    # 初始化数据库表（仅开发环境，生产环境请使用 Alembic 迁移）
    if settings.environment in ("dev", "development", "test"):
        await init_models()
        logger.info("数据库表初始化完成（开发模式）")
    else:
        # 生产环境：仅打印警告，不自动建表
        logger.info(f"跳过自动建表，请使用 Alembic 迁移")
    
    # 检测并标记卡住的文档（processing 状态但服务重启了）
    await _mark_interrupted_documents()
    
    yield  # 应用运行中...
    
    # ========== 关闭时执行 ==========
    # 这里可以添加清理逻辑，例如：
    # - 关闭数据库连接池
    # - 释放 GPU 资源
    # - 保存状态到持久存储


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,  # API 文档标题
    lifespan=lifespan,        # 生命周期管理器
    # 以下是可选配置，根据需要取消注释：
    # description="企业级知识库检索服务",
    # version="1.0.0",
    # docs_url="/docs",       # Swagger UI 路径
    # redoc_url="/redoc",     # ReDoc 路径
)

# 注册中间件（注意顺序：后添加的先执行）
app.add_middleware(AuditLogMiddleware)  # 审计日志
app.add_middleware(RequestTraceMiddleware)  # 请求追踪

# CORS 配置：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有 API 路由
# api_router 包含了所有的 API 端点（知识库、文档、查询等）
app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    """
    统一错误响应格式：
    {
        "detail": "<错误信息>",
        "code": "<ERROR_CODE>"
    }
    """
    code = "UNKNOWN_ERROR"
    detail = exc.detail
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code") or code
        detail = exc.detail.get("detail") or exc.detail.get("message") or detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "code": code},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    # 将 Pydantic 校验错误统一映射为 VALIDATION_ERROR
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "code": "VALIDATION_ERROR"},
    )
