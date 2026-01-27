"""API 路由"""

from fastapi import APIRouter
from app.api.routes import auth, users, roles, groups, ragforge, projects, dicts

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色管理"])
api_router.include_router(groups.router, prefix="/groups", tags=["部门管理"])
api_router.include_router(ragforge.router, prefix="/ragforge", tags=["RAGForge代理"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(dicts.router, prefix="/dicts", tags=["字典"])
