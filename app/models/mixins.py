"""
模型混入类 (Mixins)

提供可复用的模型字段和行为，通过多重继承添加到具体模型中。

使用示例：
    class MyModel(TimestampMixin, Base):
        __tablename__ = "my_table"
        id: Mapped[str] = mapped_column(primary_key=True)
        # 自动获得 created_at 和 updated_at 字段
"""

from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

# ==================== 类型别名 ====================
# 用于定义 UUID 格式的主键字段
# String(36) 对应 UUID 的标准格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TIMESTAMP_PK = Annotated[str, mapped_column(String(36), primary_key=True)]


class TimestampMixin:
    """
    时间戳混入类
    
    为模型添加创建时间和更新时间字段。
    这是企业应用的最佳实践，便于追踪数据变更历史。
    
    字段说明：
    - created_at: 记录创建时间，由数据库自动设置，不可修改
    - updated_at: 记录最后更新时间，每次 UPDATE 时自动更新
    
    技术细节：
    - 使用 server_default 而非 default，让数据库服务器生成时间戳
    - 使用带时区的时间类型，避免时区混乱问题
    - onupdate=func.now() 让数据库自动更新 updated_at
    """
    
    # 创建时间：记录插入时自动设置
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),   # 带时区的时间类型
        server_default=func.now(), # 使用数据库的 NOW() 函数
        nullable=False,
    )
    
    # 更新时间：每次更新记录时自动刷新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # 创建时也设置初始值
        onupdate=func.now(),        # UPDATE 时自动更新
        nullable=False,
    )
