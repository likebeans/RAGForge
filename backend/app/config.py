"""
配置管理模块

从环境变量加载配置，支持通过 .env 文件或环境变量配置。
"""

import os
import secrets
from functools import lru_cache
from pydantic_settings import BaseSettings


def generate_secret_key(length: int = 32) -> str:
    """生成安全的随机密钥"""
    return secrets.token_hex(length)


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    app_name: str = "yaoyan-backend"
    debug: bool = False

    # 数据库配置
    database_url: str = "postgresql+asyncpg://kb:kb@localhost:5435/yaoyan"

    # JWT 配置
    jwt_secret_key: str = generate_secret_key(32)
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # RAGForge 配置
    ragforge_base_url: str = ""
    ragforge_admin_key: str = ""

    # API Key 加密配置
    api_key_encryption_key: str = generate_secret_key(32)

    # CORS 配置
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @classmethod
    def validate_settings(cls, settings) -> None:
        """验证关键配置项，如果使用默认值则警告"""
        warnings = []

        if settings.jwt_secret_key == generate_secret_key(32):
            warnings.append("JWT_SECRET_KEY 使用默认值，建议在生产环境设置强密钥")

        if settings.api_key_encryption_key == generate_secret_key(32):
            warnings.append("API_KEY_ENCRYPTION_KEY 使用默认值，建议在生产环境设置强密钥")

        if settings.ragforge_admin_key == "":
            warnings.append("RAGFORGE_ADMIN_KEY 未设置，RAGForge 代理功能将不可用")

        return warnings


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    settings = Settings()
    # 验证配置
    warnings = Settings.validate_settings(settings)
    for warning in warnings:
        import warnings as py_warnings
        py_warnings.warn(warning, UserWarning)
    return settings
