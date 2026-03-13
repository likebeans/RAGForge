#!/usr/bin/env python3
"""生成示例PDF文件用于测试智能提取功能"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos

def create_pdf(filename, title, data):
    """创建项目PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    
    # 标题
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(8)
    
    # 内容
    pdf.set_font("Helvetica", size=10)
    for key, value in data.items():
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, f"{key}:", new_x=XPos.RIGHT)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.output(filename)
    print(f"Created: {filename}")


# 项目1: PD-1
data1 = {
    "Project Name": "PD-1 Monoclonal Antibody XY-101",
    "Target": "PD-1",
    "Target Type": "Antibody",
    "Drug Type": "Biologic",
    "Dosage Form": "Injection",
    "Research Stage": "Phase 2",
    "Indication": "Non-Small Cell Lung Cancer",
    "Indication Type": "Oncology",
    "ORR": "45.2%",
    "PFS": "8.5 months",
    "OS": "18.3 months",
    "Grade 3-4 AE Rate": "12.3%",
    "Asking Price (CNY)": "80,000,000",
    "Project Valuation (CNY)": "350,000,000",
    "Company Valuation (CNY)": "1,200,000,000",
    "Overall Score": "8.5",
    "Strategic Fit Score": "9.0",
    "Institution": "Beijing Innovation Biopharma",
    "Project Leader": "Dr. Zhang Ming",
    "Contact": "010-88888888",
    "Patent Expiry": "2035",
    "Risk Notes": "Phase III recruitment, competition",
}

# 项目2: CAR-T
data2 = {
    "Project Name": "CD19 CAR-T Cell Therapy CT-201",
    "Target": "CD19",
    "Target Type": "Cell Surface Antigen",
    "Drug Type": "Cell Therapy",
    "Dosage Form": "Cell Suspension",
    "Research Stage": "Phase 1",
    "Indication": "B-cell ALL",
    "Indication Type": "Hematologic Malignancy",
    "Complete Remission": "82%",
    "MRD Negative Rate": "76%",
    "6-month RFS": "68%",
    "Grade 3+ CRS Rate": "28%",
    "Asking Price (CNY)": "120,000,000",
    "Project Valuation (CNY)": "500,000,000",
    "Company Valuation (CNY)": "800,000,000",
    "Overall Score": "7.8",
    "Strategic Fit Score": "7.5",
    "Institution": "Shanghai Cell Medicine Tech",
    "Project Leader": "Prof. Li Hua",
    "Contact": "021-66666666",
    "Patent Expiry": "2038",
    "Risk Notes": "Manufacturing scale, AE management",
}

# 项目3: ADC
data3 = {
    "Project Name": "HER2-ADC Conjugate Drug ADC-301",
    "Target": "HER2",
    "Target Type": "Receptor Tyrosine Kinase",
    "Drug Type": "ADC",
    "Dosage Form": "Injection",
    "Research Stage": "Preclinical",
    "Indication": "HER2+ Breast Cancer",
    "Indication Type": "Oncology",
    "Tumor Growth Inhibition": "95%",
    "Complete Response": "40% in mice",
    "Duration of Response": ">60 days",
    "MTD in mice": "30 mg/kg",
    "Asking Price (CNY)": "50,000,000",
    "Project Valuation (CNY)": "200,000,000",
    "Company Valuation (CNY)": "500,000,000",
    "Overall Score": "7.2",
    "Strategic Fit Score": "8.0",
    "Institution": "Suzhou ADC Biotech",
    "Project Leader": "Dr. Wang Lei",
    "Contact": "0512-55555555",
    "Patent Expiry": "2040",
    "Risk Notes": "Preclinical risk, DS-8201 competition",
}

if __name__ == "__main__":
    create_pdf("/home/admin1/yaoyan_AI/test-docs/sample-pd1-project.pdf", 
               "PD-1 Inhibitor Project Report", data1)
    create_pdf("/home/admin1/yaoyan_AI/test-docs/sample-cart-project.pdf",
               "CAR-T Cell Therapy Project Report", data2)
    create_pdf("/home/admin1/yaoyan_AI/test-docs/sample-adc-project.pdf",
               "ADC Drug Project Report", data3)
    print("\nAll sample PDFs created in test-docs/")
