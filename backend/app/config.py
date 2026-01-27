"""
配置管理模块

从环境变量加载配置，参考 RAGForge 的实现方式。
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    app_name: str = "yaoyan-backend"
    debug: bool = False
    
    # 数据库配置
    database_url: str = "postgresql+asyncpg://kb:kb@localhost:5435/yaoyan"
    
    # JWT 配置
    jwt_secret_key: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    
    # RAGForge 配置
    ragforge_base_url: str = "http://192.168.168.105:8020"
    ragforge_admin_key: str = ""
    
    # API Key 加密配置
    api_key_encryption_key: str = "your-aes-key-32-bytes-long!!"
    
    # CORS 配置
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
