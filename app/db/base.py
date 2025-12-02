"""
SQLAlchemy ORM 基类定义

所有数据库模型都必须继承自这个 Base 类。
SQLAlchemy 会通过 Base.metadata 收集所有模型的表结构信息，
用于自动创建表、生成迁移脚本等。

使用示例：
    from app.db.base import Base
    
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        name = Column(String(100))
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    声明式基类
    
    SQLAlchemy 2.0 推荐使用 DeclarativeBase 作为所有 ORM 模型的基类。
    相比旧版的 declarative_base()，新的方式提供更好的类型提示支持。
    
    所有继承此类的模型都会：
    1. 自动注册到 Base.metadata
    2. 获得 ORM 映射能力
    3. 支持通过 Base.metadata.create_all() 创建表
    """
    pass
