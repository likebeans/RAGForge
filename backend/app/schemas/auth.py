"""认证相关 Schema"""

from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)
    email: str | None = None
    display_name: str | None = None


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class TokenData(BaseModel):
    """Token 数据"""
    user_id: str | None = None
