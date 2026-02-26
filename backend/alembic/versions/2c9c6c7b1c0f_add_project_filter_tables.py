"""Add project filter tables

Revision ID: 2c9c6c7b1c0f
Revises: 762401b83f4f
Create Date: 2026-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2c9c6c7b1c0f"
down_revision: Union[str, None] = "762401b83f4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drug_projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("target", sa.String(length=100), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("mechanism", sa.String(length=500), nullable=True),
        sa.Column("drug_type", sa.String(length=50), nullable=True),
        sa.Column("dosage_form", sa.String(length=50), nullable=True),
        sa.Column("research_stage", sa.String(length=50), nullable=True),
        sa.Column("indication", sa.String(length=200), nullable=True),
        sa.Column("indication_type", sa.String(length=100), nullable=True),
        sa.Column("project_highlights", sa.Text(), nullable=True),
        sa.Column("differentiation", sa.Text(), nullable=True),
        sa.Column("efficacy_indicators", sa.Text(), nullable=True),
        sa.Column("safety_indicators", sa.Text(), nullable=True),
        sa.Column("current_therapy", sa.Text(), nullable=True),
        sa.Column("competition_status", sa.Text(), nullable=True),
        sa.Column("patent_status", sa.Text(), nullable=True),
        sa.Column("patent_layout", sa.Text(), nullable=True),
        sa.Column("asking_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("project_valuation", sa.Numeric(15, 2), nullable=True),
        sa.Column("company_valuation", sa.Numeric(15, 2), nullable=True),
        sa.Column("overall_score", sa.Numeric(3, 1), nullable=True),
        sa.Column("strategic_fit_score", sa.Numeric(3, 1), nullable=True),
        sa.Column("research_institution", sa.String(length=200), nullable=True),
        sa.Column("project_leader", sa.String(length=200), nullable=True),
        sa.Column("risk_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_drug_projects_project_name", "drug_projects", ["project_name"], unique=False)
    op.create_index("idx_drug_projects_target", "drug_projects", ["target"], unique=False)
    op.create_index("idx_drug_projects_target_type", "drug_projects", ["target_type"], unique=False)
    op.create_index("idx_drug_projects_drug_type", "drug_projects", ["drug_type"], unique=False)
    op.create_index("idx_drug_projects_dosage_form", "drug_projects", ["dosage_form"], unique=False)
    op.create_index("idx_drug_projects_research_stage", "drug_projects", ["research_stage"], unique=False)
    op.create_index("idx_drug_projects_indication", "drug_projects", ["indication"], unique=False)
    op.create_index("idx_drug_projects_indication_type", "drug_projects", ["indication_type"], unique=False)
    op.create_index("idx_drug_projects_overall_score", "drug_projects", ["overall_score"], unique=False)
    op.create_index("idx_drug_projects_research_institution", "drug_projects", ["research_institution"], unique=False)
    op.create_index("idx_drug_projects_is_deleted", "drug_projects", ["is_deleted"], unique=False)

    op.create_table(
        "dict_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("category", "code", name="uq_dict_items_category_code"),
    )

    op.create_index("idx_dict_items_category", "dict_items", ["category"], unique=False)
    op.create_index("idx_dict_items_is_active", "dict_items", ["is_active"], unique=False)

    dict_rows = [
        ("target_type", "gpcr", "GPCR", 1),
        ("target_type", "kinase", "激酶", 2),
        ("target_type", "antibody", "抗体靶点", 3),
        ("target_type", "ion_channel", "离子通道", 4),
        ("target_type", "nuclear_receptor", "核受体", 5),
        ("target_type", "other", "其他", 99),
        ("drug_type", "small_molecule", "小分子药", 1),
        ("drug_type", "biologic", "生物药", 2),
        ("drug_type", "adc", "ADC", 3),
        ("drug_type", "cell_therapy", "细胞治疗", 4),
        ("drug_type", "gene_therapy", "基因治疗", 5),
        ("drug_type", "other", "其他", 99),
        ("dosage_form", "tablet", "片剂", 1),
        ("dosage_form", "injection", "注射剂", 2),
        ("dosage_form", "capsule", "胶囊", 3),
        ("dosage_form", "oral_solution", "口服液", 4),
        ("dosage_form", "patch", "贴剂", 5),
        ("dosage_form", "other", "其他", 99),
        ("research_stage", "preclinical", "临床前", 1),
        ("research_stage", "phase1", "I期", 2),
        ("research_stage", "phase2", "II期", 3),
        ("research_stage", "phase3", "III期", 4),
        ("research_stage", "nda", "上市申请", 5),
        ("research_stage", "approved", "已上市", 6),
        ("indication_type", "oncology", "肿瘤", 1),
        ("indication_type", "autoimmune", "自身免疫性疾病", 2),
        ("indication_type", "infectious", "感染性疾病", 3),
        ("indication_type", "cardiovascular", "心血管疾病", 4),
        ("indication_type", "neurological", "神经系统疾病", 5),
        ("indication_type", "metabolic", "代谢性疾病", 6),
        ("indication_type", "rare_disease", "罕见病", 7),
        ("indication_type", "other", "其他", 99),
    ]

    op.bulk_insert(
        sa.table(
            "dict_items",
            sa.column("category", sa.String),
            sa.column("code", sa.String),
            sa.column("label", sa.String),
            sa.column("sort_order", sa.Integer),
            sa.column("is_active", sa.Boolean),
        ),
        [
            {
                "category": category,
                "code": code,
                "label": label,
                "sort_order": sort_order,
                "is_active": True,
            }
            for (category, code, label, sort_order) in dict_rows
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_dict_items_is_active", table_name="dict_items")
    op.drop_index("idx_dict_items_category", table_name="dict_items")
    op.drop_table("dict_items")

    op.drop_index("idx_drug_projects_is_deleted", table_name="drug_projects")
    op.drop_index("idx_drug_projects_research_institution", table_name="drug_projects")
    op.drop_index("idx_drug_projects_overall_score", table_name="drug_projects")
    op.drop_index("idx_drug_projects_indication_type", table_name="drug_projects")
    op.drop_index("idx_drug_projects_indication", table_name="drug_projects")
    op.drop_index("idx_drug_projects_research_stage", table_name="drug_projects")
    op.drop_index("idx_drug_projects_dosage_form", table_name="drug_projects")
    op.drop_index("idx_drug_projects_drug_type", table_name="drug_projects")
    op.drop_index("idx_drug_projects_target_type", table_name="drug_projects")
    op.drop_index("idx_drug_projects_target", table_name="drug_projects")
    op.drop_index("idx_drug_projects_project_name", table_name="drug_projects")
    op.drop_table("drug_projects")
