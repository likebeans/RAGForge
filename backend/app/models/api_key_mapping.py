"""API Key 映射模型"""

from uuid import uuid4
from sqlalchemy import String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class APIKeyMapping(TimestampMixin, Base):
    """yaoyan 用户 → RAGForge API Key 映射表"""
    __tablename__ = "api_key_mappings"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    ragforge_key_id: Mapped[str | None] = mapped_column(String(100))
    ragforge_api_key: Mapped[str | None] = mapped_column(Text)
    identity_snapshot: Mapped[dict | None] = mapped_column(JSON)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    
    user: Mapped["User"] = relationship("User", back_populates="api_key_mapping")
