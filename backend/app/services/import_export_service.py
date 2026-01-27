"""Excel 导入导出服务"""

import io
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DrugProject
from app.services.project_service import ProjectService


class ImportExportService:
    """Excel 导入导出服务"""

    # Excel 列映射（与模板对应）
    COLUMN_MAPPING = {
        "A": ("project_name", "项目/药物名称"),
        "B": ("target", "靶点"),
        "C": ("target_type", "靶点类型"),
        "D": ("mechanism", "作用机制"),
        "E": ("drug_type", "药物类型"),
        "F": ("dosage_form", "药物剂型"),
        "G": ("research_stage", "研究阶段"),
        "H": ("indication", "适应症"),
        "I": ("indication_type", "适应症类型"),
        "J": ("project_highlights", "项目亮点"),
        "K": ("differentiation", "差异化创新点"),
        "L": ("efficacy_indicators", "主要药效指标"),
        "M": ("safety_indicators", "主要安全性指标"),
        "N": ("current_therapy", "当前标准疗法及疗效"),
        "O": ("competition_status", "赛道竞争情况"),
        "P": ("patent_status", "专利情况"),
        "Q": ("patent_layout", "专利布局"),
        "R": ("asking_price", "报价与估值(万元)"),
        "S": ("project_valuation", "项目估值(万元)"),
        "T": ("company_valuation", "公司估值(万元)"),
        "U": ("overall_score", "综合评分(0-10)"),
        "V": ("strategic_fit_score", "战略匹配度(0-10)"),
        "W": ("research_institution", "研发机构"),
        "X": ("project_leader", "项目负责人/创始人"),
        "Y": ("risk_notes", "风险提示"),
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)

    def create_template(self) -> io.BytesIO:
        """创建 Excel 导入模板"""
        wb = Workbook()
        ws = wb.active
        ws.title = "项目数据"

        # 设置标题行样式
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # 写入标题行
        for col, (field, label) in self.COLUMN_MAPPING.items():
            cell = ws[f"{col}1"]
            cell.value = label
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        # 写入示例数据行
        example_data = {
            "A": "PD-1抑制剂示例项目",
            "B": "PD-1",
            "C": "antibody",
            "D": "阻断PD-1/PD-L1通路",
            "E": "biologic",
            "F": "injection",
            "G": "phase2",
            "H": "非小细胞肺癌",
            "I": "oncology",
            "J": "针对亚洲人群优化",
            "K": "更高的应答率和更低的副作用",
            "L": "ORR 45%, PFS 8.5个月",
            "M": "3-4级不良事件发生率 < 15%",
            "N": "标准化疗方案，ORR 20-30%",
            "O": "国内已有5款PD-1产品上市，竞争激烈",
            "P": "核心专利2030年到期",
            "Q": "中国、美国、欧洲已申请专利",
            "R": "5000",
            "S": "50000",
            "T": "200000",
            "U": "8.5",
            "V": "9.0",
            "W": "某生物科技有限公司",
            "X": "张博士 (13800138000)",
            "Y": "临床风险、市场竞争风险",
        }

        for col, value in example_data.items():
            ws[f"{col}2"] = value

        # 设置列宽
        for col in self.COLUMN_MAPPING.keys():
            ws.column_dimensions[col].width = 20

        # 冻结首行
        ws.freeze_panes = "A2"

        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    async def import_from_excel(
        self, file_content: bytes, mode: str = "append", created_by: str | None = None
    ) -> dict:
        """
        从 Excel 导入项目数据

        Args:
            file_content: Excel 文件内容
            mode: 导入模式 (append: 追加, replace: 替换全部)
            created_by: 创建者用户ID

        Returns:
            导入结果统计
        """
        wb = load_workbook(io.BytesIO(file_content))
        ws = wb.active

        # 如果是替换模式，先清空现有数据
        if mode == "replace":
            # 这里使用软删除，标记所有项目为已删除
            from sqlalchemy import update
            await self.db.execute(update(DrugProject).values(is_deleted=True))
            await self.db.commit()

        success_count = 0
        error_count = 0
        errors = []

        # 从第2行开始读取数据（第1行是标题）
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # 构建项目数据
                project_data = {}
                for col_idx, (col, (field, _)) in enumerate(self.COLUMN_MAPPING.items()):
                    value = row[col_idx] if col_idx < len(row) else None

                    # 跳过空值
                    if value is None or (isinstance(value, str) and not value.strip()):
                        continue

                    # 类型转换
                    if field in ["asking_price", "project_valuation", "company_valuation"]:
                        try:
                            project_data[field] = float(value)
                        except (ValueError, TypeError):
                            pass
                    elif field in ["overall_score", "strategic_fit_score"]:
                        try:
                            project_data[field] = float(value)
                        except (ValueError, TypeError):
                            pass
                    else:
                        project_data[field] = str(value).strip()

                # 必填字段检查
                if "project_name" not in project_data or not project_data["project_name"]:
                    errors.append(f"第 {row_idx} 行：项目名称不能为空")
                    error_count += 1
                    continue

                # 创建项目
                project = DrugProject(**project_data, created_by=created_by)
                await self.project_service.create(project)
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"第 {row_idx} 行：{str(e)}")

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:10],  # 最多返回前10条错误
            "mode": mode,
        }

    async def export_to_excel(
        self,
        page: int = 1,
        page_size: int = 1000,
        **filters,
    ) -> io.BytesIO:
        """
        导出项目数据到 Excel

        Args:
            page: 页码
            page_size: 每页数量（最大1000）
            **filters: 筛选条件

        Returns:
            Excel 文件内容
        """
        # 查询项目数据
        items, total = await self.project_service.query_projects(
            page=page, page_size=min(page_size, 1000), **filters
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "项目数据"

        # 设置标题行样式
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # 写入标题行
        for col, (field, label) in self.COLUMN_MAPPING.items():
            cell = ws[f"{col}1"]
            cell.value = label
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        # 写入数据行
        for row_idx, project in enumerate(items, start=2):
            for col, (field, _) in self.COLUMN_MAPPING.items():
                value = getattr(project, field, None)
                if value is not None:
                    ws[f"{col}{row_idx}"] = value

        # 设置列宽
        for col in self.COLUMN_MAPPING.keys():
            ws.column_dimensions[col].width = 20

        # 冻结首行
        ws.freeze_panes = "A2"

        # 添加统计信息
        ws = wb.create_sheet("统计信息")
        ws["A1"] = "导出时间"
        ws["B1"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws["A2"] = "总记录数"
        ws["B2"] = total
        ws["A3"] = "当前导出"
        ws["B3"] = len(items)

        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
