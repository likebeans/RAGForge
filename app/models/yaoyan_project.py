"""
Yaoyan 项目模型

从 yaoyan 项目复制，用于在 RAGForge 中操作项目数据。
"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Numeric,
    DateTime,
    Enum,
    JSON,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DevPhaseEnum(str, enum.Enum):
    PRE_CLINICAL = "PRE_CLINICAL"
    PHASE_I = "PHASE_I"
    PHASE_II = "PHASE_II"
    PHASE_III = "PHASE_III"
    NDA = "NDA"
    APPROVED = "APPROVED"


class OverallStatusEnum(str, enum.Enum):
    SCREENING = "SCREENING"
    IN_PROGRESS = "IN_PROGRESS"
    ARCHIVED = "ARCHIVED"
    MONITORING = "MONITORING"
    RESTARTED = "RESTARTED"


class ProjectMaster(Base):
    """项目主画像表"""

    __tablename__ = "project_master"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    target_id: Mapped[str | None] = mapped_column(String(100), index=True)
    indication: Mapped[str | None] = mapped_column(String(255), index=True)
    dev_phase: Mapped[DevPhaseEnum | None] = mapped_column(
        Enum(DevPhaseEnum), index=True
    )
    overall_status: Mapped[OverallStatusEnum] = mapped_column(
        Enum(OverallStatusEnum), default=OverallStatusEnum.SCREENING, index=True
    )
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1), index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProjectDetail(Base):
    """项目研发与临床详情表"""

    __tablename__ = "project_details"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drug_type: Mapped[str | None] = mapped_column(String(100))
    dosage_form: Mapped[str | None] = mapped_column(String(100))
    mechanism: Mapped[str | None] = mapped_column(Text)
    project_highlights: Mapped[str | None] = mapped_column(Text)
    differentiation: Mapped[str | None] = mapped_column(Text)
    efficacy_indicators: Mapped[dict | None] = mapped_column(JSONB)
    safety_indicators: Mapped[dict | None] = mapped_column(JSONB)
    current_therapy: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProjectValuation(Base):
    """项目商业与估值表"""

    __tablename__ = "project_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_master.id", ondelete="CASCADE"), index=True
    )
    asking_price: Mapped[float | None] = mapped_column(Numeric(15, 2))
    project_valuation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    company_valuation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    strategic_fit_score: Mapped[float | None] = mapped_column(Numeric(3, 1))
    valuation_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProjectManagementInfo(Base):
    """项目内部管理信息表"""

    __tablename__ = "project_management_info"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_leader_id: Mapped[str | None] = mapped_column(String(36), index=True)
    risk_notes: Mapped[str | None] = mapped_column(Text)
    follow_up_records: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ResearchDetail(Base):
    """尽调调研明细表"""

    __tablename__ = "research_details"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        primary_key=True,
    )
    market_json: Mapped[dict | None] = mapped_column(JSONB)
    target_mech: Mapped[str | None] = mapped_column(Text)
    competitor_data: Mapped[dict | None] = mapped_column(JSONB)
    patent_json: Mapped[dict | None] = mapped_column(JSONB)
    policy_impact: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def create_project_id() -> str:
    """生成项目ID"""
    return str(uuid4())
