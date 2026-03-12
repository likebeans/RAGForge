"""创新药项目模型

此模块包含创新药项目核心表及其关联表。
基于 "项目表结构拆分方案" 设计：
1. ProjectMaster: 核心基础信息
2. ProjectDetail: 研发临床长文本详情 (1:1)
3. ProjectValuation: 融资与估值历史 (1:N)
4. ResearchDetail: 外部尽调JSON数据 (1:1)
5. TargetDict: 靶点标准字典库
6. ProjectManagementInfo: 内部管理跟进与风险 (1:1)
7. ProjectInstitutionLink: 机构关联中间表 (N:M)
"""

from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Boolean, Integer, Numeric, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
from app.models.mixins import TimestampMixin
import enum

# ==========================================
# 辅助枚举
# ==========================================
class DevPhaseEnum(str, enum.Enum):
    PRE_CLINICAL = "PRE_CLINICAL"
    PHASE_I      = "PHASE_I"
    PHASE_II     = "PHASE_II"
    PHASE_III    = "PHASE_III"
    NDA          = "NDA"
    APPROVED     = "APPROVED"

class OverallStatusEnum(str, enum.Enum):
    SCREENING   = "SCREENING"
    IN_PROGRESS = "IN_PROGRESS"
    ARCHIVED    = "ARCHIVED"
    MONITORING  = "MONITORING"
    RESTARTED   = "RESTARTED"

class InstitutionRoleEnum(str, enum.Enum):
    ORIGINATOR = "原研"
    CO_DEVELOPER = "共同开发"
    INVESTOR = "投资机构"

# ==========================================
# 靶点标准字典库
# ==========================================
class TargetDict(TimestampMixin, Base):
    """靶点标准字典库"""
    __tablename__ = "target_dict"

    id: Mapped[str] = mapped_column(String(100), primary_key=True) # target_id
    standard_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    aliases: Mapped[dict | None] = mapped_column(JSONB)
    moa_default: Mapped[str | None] = mapped_column(Text)

# ==========================================
# 机构关联表(N:M 中间表)
# ==========================================
class ProjectInstitutionLink(TimestampMixin, Base):
    """项目与机构关联表"""
    __tablename__ = "project_institution_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_master.id", ondelete="CASCADE"), index=True)
    institution_id: Mapped[str] = mapped_column(String(36), index=True) # 未来可外键关联 Institution 表
    role_type: Mapped[InstitutionRoleEnum] = mapped_column(Enum(InstitutionRoleEnum), default=InstitutionRoleEnum.ORIGINATOR)

# ==========================================
# 核心主画像表
# ==========================================
class ProjectMaster(TimestampMixin, Base):
    """项目主画像表"""
    __tablename__ = "project_master"

    id: Mapped[str] = mapped_column(String(36), primary_key=True) # project_id
    project_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), ForeignKey("target_dict.id", ondelete="SET NULL"), index=True)
    indication: Mapped[str | None] = mapped_column(String(255), index=True)
    dev_phase: Mapped[DevPhaseEnum | None] = mapped_column(Enum(DevPhaseEnum), index=True)
    overall_status: Mapped[OverallStatusEnum] = mapped_column(Enum(OverallStatusEnum), default=OverallStatusEnum.SCREENING, index=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1), index=True)

    # 系统字段
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # 关联关系
    target_info: Mapped["TargetDict"] = relationship(lazy="joined")
    detail: Mapped["ProjectDetail"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    management_info: Mapped["ProjectManagementInfo"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    research_detail: Mapped["ResearchDetail"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    valuations: Mapped[list["ProjectValuation"]] = relationship(back_populates="project", cascade="all, delete-orphan")

# ==========================================
# 1:1 附属表
# ==========================================
class ProjectDetail(TimestampMixin, Base):
    """项目研发与临床详情表"""
    __tablename__ = "project_details"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_master.id", ondelete="CASCADE"), primary_key=True)
    drug_type: Mapped[str | None] = mapped_column(String(100))
    dosage_form: Mapped[str | None] = mapped_column(String(100))
    mechanism: Mapped[str | None] = mapped_column(Text)
    project_highlights: Mapped[str | None] = mapped_column(Text)
    differentiation: Mapped[str | None] = mapped_column(Text)
    efficacy_indicators: Mapped[dict | None] = mapped_column(JSONB)
    safety_indicators: Mapped[dict | None] = mapped_column(JSONB)
    current_therapy: Mapped[str | None] = mapped_column(Text)

    project: Mapped["ProjectMaster"] = relationship(back_populates="detail")

class ResearchDetail(TimestampMixin, Base):
    """尽调调研明细表"""
    __tablename__ = "research_details"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_master.id", ondelete="CASCADE"), primary_key=True)
    market_json: Mapped[dict | None] = mapped_column(JSONB)
    target_mech: Mapped[str | None] = mapped_column(Text)
    competitor_data: Mapped[dict | None] = mapped_column(JSONB)
    patent_json: Mapped[dict | None] = mapped_column(JSONB)
    policy_impact: Mapped[str | None] = mapped_column(Text)

    project: Mapped["ProjectMaster"] = relationship(back_populates="research_detail")

class ProjectManagementInfo(TimestampMixin, Base):
    """项目内部管理信息表"""
    __tablename__ = "project_management_info"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_master.id", ondelete="CASCADE"), primary_key=True)
    project_leader_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    risk_notes: Mapped[str | None] = mapped_column(Text)
    follow_up_records: Mapped[dict | None] = mapped_column(JSONB)

    project: Mapped["ProjectMaster"] = relationship(back_populates="management_info")

# ==========================================
# 1:N 附属表
# ==========================================
class ProjectValuation(TimestampMixin, Base):
    """项目商业与估值表"""
    __tablename__ = "project_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_master.id", ondelete="CASCADE"), index=True)
    asking_price: Mapped[float | None] = mapped_column(Numeric(15, 2))
    project_valuation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    company_valuation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    strategic_fit_score: Mapped[float | None] = mapped_column(Numeric(3, 1))
    valuation_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["ProjectMaster"] = relationship(back_populates="valuations")

# 为了向下兼容在迁移期间暂留 DrugProject，随后会被移除
# class DrugProject(TimestampMixin, Base):
#     ...
