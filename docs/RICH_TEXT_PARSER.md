# 富文本文件解析功能开发方案

> **版本**: v1.2  
> **更新时间**: 2026-02-04  
> **作者**: RAGForge Team  
> **状态**: ✅ 已完成基础功能实现

## 📋 实现状态总览

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| Excel 解析器 | ✅ 已完成 | 支持 xlsx/xls，表格转 Markdown |
| Word 解析器 | ✅ 已完成 | 支持 docx，段落+表格提取 |
| PDF 解析器 | ✅ 已完成 | MinerU 集成 + PyMuPDF 回退 |
| 文件上传接口 | ✅ 已完成 | 支持多格式，50MB 限制 |
| MinIO 服务 | ✅ 已部署 | Docker Compose 集成 |
| OSS 存储 | ✅ 已完成 | 原始文件自动保存 |
| 数据库字段 | ✅ 已完成 | Document 表添加 OSS 路径 |
| Schema 提取 | ✅ 已完成 | xlsx 模板字段提取 |
| PDF字段提取→Excel | ✅ 已完成 | PDF解析→LLM字段提取→Excel导出 |

---

## 📌 PDF 字段提取到 Excel 完整流程

### 核心流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PDF 字段提取到 Excel 完整流程                          │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐                                           
  │   用户上传   │                                           
  │ Excel 模板  │  定义要提取的字段                          
  │ (字段定义)  │  如：产品名称、价格、规格、日期             
  └──────┬───────┘                                           
         │                                                   
         ▼                                                   
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Step 1:    │     │  Step 2:    │     │  Step 3:    │
  │  解析模板   │────▶│  创建Schema │────▶│  保存Schema │
  │ (Excel→字段)│     │  (字段列表) │     │  (数据库)   │
  └──────────────┘     └──────────────┘     └──────────────┘
                                                    │
                                                    ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                           Schema (提取模板)                               │
  │  {                                                                        │
  │    "id": "schema-123",                                                   │
  │    "name": "产品信息提取",                                                │
  │    "fields": [                                                            │
  │      {"name": "产品名称", "type": "string"},                             │
  │      {"name": "规格型号", "type": "string"},                             │
  │      {"name": "价格", "type": "number"},                                 │
  │      {"name": "生产日期", "type": "date"}                                │
  │    ]                                                                      │
  │  }                                                                        │
  └──────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
  ┌──────────────┐                                           
  │   用户上传   │                                           
  │  PDF 文件   │  需要提取信息的源文件                       
  │ (多个文件)  │                                            
  └──────┬───────┘                                           
         │                                                   
         ▼                                                   
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Step 4:    │     │  Step 5:    │     │  Step 6:    │
  │  PDF 解析   │────▶│  转 Markdown │────▶│  全文内容   │
  │  (MinerU)   │     │  (结构化)   │     │  (含表格)   │
  └──────────────┘     └──────────────┘     └──────────────┘
                                                    │
                                                    ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                         Markdown 内容示例                                 │
  │  # 产品说明书                                                             │
  │                                                                           │
  │  ## 基本信息                                                              │
  │  | 项目 | 内容 |                                                          │
  │  |------|------|                                                          │
  │  | 产品名称 | 益生菌胶囊 |                                                │
  │  | 规格型号 | 500mg×60粒 |                                                │
  │  | 价格 | ¥199.00 |                                                       │
  │  | 生产日期 | 2024-01-15 |                                                │
  │  ...                                                                      │
  └──────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Step 7:    │     │  Step 8:    │     │  Step 9:    │
  │  LLM 提取   │────▶│  JSON 结果  │────▶│  生成 Excel │
  │(按Schema提取)│     │ (结构化数据)│     │  (导出下载) │
  └──────────────┘     └──────────────┘     └──────────────┘
                              │                     │
                              ▼                     ▼
  ┌────────────────────────────────┐   ┌────────────────────────────────┐
  │  {                             │   │  输出 Excel:                    │
  │    "产品名称": "益生菌胶囊",    │   │  ┌─────────┬─────────┬─────┐   │
  │    "规格型号": "500mg×60粒",    │   │  │产品名称 │规格型号 │价格 │   │
  │    "价格": 199.00,             │   │  ├─────────┼─────────┼─────┤   │
  │    "生产日期": "2024-01-15"    │   │  │益生菌.. │500mg×60│ 199 │   │
  │  }                             │   │  │维生素.. │100mg×30│  89 │   │
  └────────────────────────────────┘   │  └─────────┴─────────┴─────┘   │
                                       └────────────────────────────────┘
```

### 各步骤详解

#### Step 1-3: 创建提取模板 (Schema)

**用户操作**：上传一个 Excel 文件作为模板，定义要提取的字段

**Excel 模板格式**：
```
| 字段名称 | 字段类型 | 是否必填 | 说明 |
|----------|----------|----------|------|
| 产品名称 | string   | 是       | 产品的官方名称 |
| 规格型号 | string   | 否       | 产品的规格描述 |
| 价格     | number   | 否       | 产品单价（数字） |
| 生产日期 | date     | 否       | 格式：YYYY-MM-DD |
```

**系统处理**：
```python
# ExcelParser.extract_schema() 从 Excel 提取字段定义
schema = parser.extract_schema(excel_bytes, name="产品信息提取")
# 返回:
# ExtractionSchema(
#     id="uuid-xxx",
#     name="产品信息提取",
#     fields=[
#         {"name": "产品名称", "type": "string", "required": True},
#         {"name": "规格型号", "type": "string", "required": False},
#         {"name": "价格", "type": "number", "required": False},
#         {"name": "生产日期", "type": "date", "required": False},
#     ],
#     source_file="template.xlsx"
# )
```

#### Step 4-6: PDF 解析为 Markdown

**用户操作**：上传需要提取信息的 PDF 文件

**系统处理**：
```python
# PDFParser 调用 MinerU 服务解析 PDF
from app.pipeline.parsers.pdf_parser import PDFParser
from app.infra.mineru_client import MinerUClient

parser = PDFParser()
result = await parser.parse(pdf_bytes, "product_catalog.pdf")

# result.content 包含完整的 Markdown 格式内容
# - 文本段落保持原有结构
# - 表格转换为 Markdown 表格
# - 公式转换为 LaTeX 格式
# - 图片提取为独立文件或 Base64
```

**MinerU 输出示例**：
```markdown
# 产品说明书

## 一、产品概述

本产品为高品质益生菌胶囊，采用先进的包埋技术...

## 二、产品信息

| 项目 | 内容 |
|------|------|
| 产品名称 | 益生菌胶囊 |
| 规格型号 | 500mg×60粒/瓶 |
| 执行标准 | GB/T XXXXX |
| 零售价格 | ¥199.00 |
| 生产日期 | 2024-01-15 |
| 保质期 | 24个月 |

## 三、成分表

| 成分 | 含量 | 单位 |
|------|------|------|
| 乳酸菌 | 100亿 | CFU |
| 双歧杆菌 | 50亿 | CFU |
...
```

#### Step 7-8: LLM 按 Schema 提取字段

**系统处理**：
```python
# PDFParser._extract_with_schema() 调用 LLM 提取字段
extracted_fields = await parser._extract_with_schema(
    content=markdown_content,
    schema=extraction_schema
)

# LLM Prompt 示例:
"""
请从以下文档内容中提取指定字段的信息。

## 需要提取的字段
- 产品名称 (string)
- 规格型号 (string)
- 价格 (number)
- 生产日期 (date)

## 文档内容
{markdown_content}

## 输出要求
1. 严格按照 JSON 格式返回
2. 如果某字段未找到，设为 null
3. 价格字段仅保留数字
4. 日期字段格式化为 YYYY-MM-DD

请直接返回 JSON：
"""

# LLM 返回:
{
    "产品名称": "益生菌胶囊",
    "规格型号": "500mg×60粒/瓶",
    "价格": 199.00,
    "生产日期": "2024-01-15"
}
```

#### Step 9: 生成 Excel 导出

**系统处理**：
```python
# 批量处理多个 PDF，汇总结果导出 Excel
import openpyxl
from io import BytesIO

def generate_excel(schema: ExtractionSchema, results: list[dict]) -> bytes:
    """将提取结果生成 Excel 文件"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "提取结果"
    
    # 写入表头（从 Schema 获取字段名）
    headers = [f["name"] for f in schema.fields]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=header)
    
    # 写入数据行
    for row_idx, result in enumerate(results, start=2):
        for col, header in enumerate(headers, start=1):
            ws.cell(row=row_idx, column=col, value=result.get(header))
    
    # 导出为 bytes
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
```

**输出 Excel 示例**：

| 产品名称 | 规格型号 | 价格 | 生产日期 |
|----------|----------|------|----------|
| 益生菌胶囊 | 500mg×60粒 | 199 | 2024-01-15 |
| 维生素C片 | 100mg×30片 | 89 | 2024-02-20 |
| 蛋白粉 | 1kg/罐 | 299 | 2024-03-10 |

### API 设计

#### 1. 创建提取模板

```bash
POST /v1/extraction-schemas
Content-Type: multipart/form-data

file: template.xlsx        # Excel 模板文件（定义字段）
name: 产品信息提取          # 模板名称
```

**响应**：
```json
{
  "id": "schema-123",
  "name": "产品信息提取",
  "fields": [
    {"name": "产品名称", "type": "string", "required": true},
    {"name": "规格型号", "type": "string", "required": false},
    {"name": "价格", "type": "number", "required": false},
    {"name": "生产日期", "type": "date", "required": false}
  ]
}
```

#### 2. 批量提取 PDF 字段

```bash
POST /v1/extraction-schemas/{schema_id}/extract
Content-Type: multipart/form-data

files[]: product1.pdf      # 多个 PDF 文件
files[]: product2.pdf
files[]: product3.pdf
output_format: excel       # 输出格式：json / excel
```

**响应（JSON 格式）**：
```json
{
  "results": [
    {
      "filename": "product1.pdf",
      "fields": {
        "产品名称": "益生菌胶囊",
        "规格型号": "500mg×60粒",
        "价格": 199,
        "生产日期": "2024-01-15"
      }
    },
    {
      "filename": "product2.pdf",
      "fields": {
        "产品名称": "维生素C片",
        "规格型号": "100mg×30片",
        "价格": 89,
        "生产日期": "2024-02-20"
      }
    }
  ],
  "total": 2,
  "success": 2,
  "failed": 0
}
```

**响应（Excel 格式）**：
```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="extraction_result.xlsx"

<Excel 二进制内容>
```

#### 3. 使用示例（完整流程）

```bash
# 1. 上传 Excel 模板，创建 Schema
SCHEMA_ID=$(curl -X POST "$BASE_URL/v1/extraction-schemas" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@template.xlsx" \
  -F "name=产品信息提取" | jq -r '.id')

echo "创建 Schema: $SCHEMA_ID"

# 2. 批量上传 PDF，按 Schema 提取字段，导出 Excel
curl -X POST "$BASE_URL/v1/extraction-schemas/$SCHEMA_ID/extract" \
  -H "Authorization: Bearer $API_KEY" \
  -F "files[]=@product1.pdf" \
  -F "files[]=@product2.pdf" \
  -F "files[]=@product3.pdf" \
  -F "output_format=excel" \
  --output extraction_result.xlsx

echo "提取完成，结果已保存到 extraction_result.xlsx"
```

### 技术实现要点

#### 1. MinerU 配置（可选线上/自部署）

```bash
# .env
MINERU_ENABLED=true                          # 是否启用 MinerU
MINERU_BASE_URL=http://localhost:8010        # 自部署地址
MINERU_API_KEY=                              # API Key（云服务）
MINERU_TIMEOUT=300                           # 超时时间（秒）
```

#### 2. LLM 配置（用于字段提取）

提取使用 **租户级 LLM 配置**，通过 `model_config_resolver` 获取：
- **优先级**：租户级 > 系统级 > 环境变量
- **支持多提供商**：qwen/zhipu/siliconflow/openai/ollama 等
- **无 LLM 时**：返回 `{"_warning": "未配置 LLM"}` 警告，不会报错

**配置方式**：

```bash
# 方式 1: 环境变量（全局默认）
LLM_PROVIDER=qwen
LLM_MODEL=qwen-turbo
QWEN_API_KEY=sk-xxx

# 方式 2: 租户级配置（通过 Admin API）
curl -X PATCH "$BASE_URL/admin/tenants/{tenant_id}" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_config": {
      "llm": {
        "provider": "siliconflow",
        "model": "Qwen/Qwen2.5-7B-Instruct"
      }
    }
  }'
```

#### 3. 文件存储与入库说明

**PDF 提取支持两种模式**：

| 模式 | 参数 | 行为 | 适用场景 |
|------|------|------|----------|
| **仅提取** | 不传 `kb_id` | 提取字段后丢弃 PDF | 临时数据处理 |
| **提取+入库** | 传入 `kb_id` | 提取字段 + 异步存储 OSS + 入库知识库 | 需要后续检索 |

**提取+入库流程**（指定 `kb_id` 时）：
```
PDF 上传 → 内存解析 → LLM 提取 → 立即返回结果
                              ↓
                    [异步后台任务]
                              ↓
            PDF 存储到 OSS → Markdown 切分 → 向量化 → 入库知识库
```

**API 调用示例**：
```bash
# 仅提取（不入库）
curl -X POST "$BASE_URL/v1/extraction-schemas/$SCHEMA_ID/extract" \
  -H "Authorization: Bearer $API_KEY" \
  -F "files[]=@product.pdf" \
  -F "output_format=json"

# 提取 + 入库到知识库（异步）
curl -X POST "$BASE_URL/v1/extraction-schemas/$SCHEMA_ID/extract" \
  -H "Authorization: Bearer $API_KEY" \
  -F "files[]=@product.pdf" \
  -F "output_format=json" \
  -F "kb_id=$KB_ID"
```

**入库后的数据**：
- **OSS 路径**: `oss://ragforge/{tenant_id}/raw/{doc_id}/{filename}`
- **Document 记录**: 包含提取的字段元数据
- **Chunks**: PDF 转 Markdown 后切分入库，支持语义检索

#### 4. 错误处理

| 场景 | 处理方式 |
|------|----------|
| MinerU 不可用 | 回退到 PyMuPDF 本地解析 |
| PDF 解析失败 | 返回错误，跳过该文件 |
| LLM 提取失败 | 重试 1 次，仍失败则标记为提取失败 |
| JSON 解析失败 | 返回原始 LLM 响应，标记解析错误 |

#### 5. 性能优化

- **异步处理**：多个 PDF 并发解析
- **批量 LLM 调用**：支持批量提取减少 API 调用次数
- **缓存**：相同 PDF Hash 跳过重复解析

### 实现状态（2026-02-04 验证通过）

#### 已实现文件

| 文件 | 说明 |
|------|------|
| `app/models/extraction_schema.py` | ExtractionSchema ORM 模型 |
| `app/schemas/extraction_schema.py` | Pydantic 请求/响应模型 |
| `app/api/routes/extraction.py` | 提取模板管理 API |
| `app/pipeline/parsers/excel_parser.py` | Excel 模板解析（extract_schema） |
| `app/pipeline/parsers/pdf_parser.py` | PDF 解析 + LLM 字段提取 |
| `alembic/versions/20250204_0001_*.py` | 数据库迁移脚本 |
| `tests/test_extraction_api.py` | API 测试脚本 |

#### 测试结果

**基础功能测试**（无 LLM 配置）：
```bash
# 运行测试
ADMIN_TOKEN=ragforge-admin-2024 uv run python tests/test_extraction_api.py

# 输出
[1] 创建测试租户... ✅
[2] 创建提取模板... ✅ (4 字段)
[3] 列出提取模板... ✅
[4] 获取提取模板详情... ✅
[5] 测试 PDF 提取...
    - JSON 输出: ✅ (200 OK, 返回警告信息)
    - Excel 输出: ✅ (5KB xlsx 文件)
```

**完整流程测试**（使用配置了 LLM 的租户 `test-tenant`）：
```python
# 租户配置
tenant_id: a61c607a-d631-49d2-80c6-f2cdd8cd7d7b
model_settings: {
  "providers": {
    "qwen": {"api_key": "sk-xxx", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"}
  },
  "defaults": {
    "llm": {"provider": "qwen", "model": "qwen-plus-2025-12-01"}
  }
}

# 测试结果
[1] 创建 Excel 模板... ✅
[2] 创建提取模板... ✅ (Schema ID: fa1baff3-553d-415f-b9c0-1afd4f90eb93)
[3] 创建测试 PDF... ✅
[4] 测试 PDF 提取... ✅
    总数: 1, 成功: 1, 失败: 0
    提取字段: {
      "产品名称": "Premium Wireless Headphones",
      "价格": 299.99,
      "规格": "Bluetooth 5.0, 40mm drivers",
      "生产日期": "2024-01-15"
    }
```

#### 依赖说明

- **PDF 解析**: MinerU（优先） 或 PyMuPDF（回退）
- **LLM 提取**: 自动使用租户级 > 系统级 > 环境变量 LLM 配置
- **Excel 生成**: openpyxl

#### LLM 配置说明

字段提取使用 `model_config_resolver` 自动获取 LLM 配置：

| 配置层级 | 优先级 | 配置方式 |
|----------|--------|----------|
| 租户级 | 高 | Admin API 更新 `model_config.llm` |
| 系统级 | 中 | 数据库 `system_configs` 表 |
| 环境变量 | 低 | `LLM_PROVIDER`, `LLM_MODEL` |

**无 LLM 时的行为**：
- 返回 `{"_warning": "未配置 LLM，请在租户设置或环境变量中配置 LLM 提供商"}`
- PDF 解析正常完成，仅字段提取跳过
- 不会抛出异常，保证流程可用性

**如何为租户配置 LLM**：

```bash
# 方式 1: 通过 Admin API 配置租户级 LLM
curl -X PATCH "http://localhost:8020/admin/tenants/{tenant_id}" \
  -H "X-Admin-Token: ragforge-admin-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "model_settings": {
      "providers": {
        "qwen": {
          "api_key": "sk-xxx",
          "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }
      },
      "defaults": {
        "llm": {
          "provider": "qwen",
          "model": "qwen-plus-2025-12-01"
        }
      }
    }
  }'

# 方式 2: 配置环境变量（全局默认）
# 在 .env 或 docker-compose.yml 中添加：
LLM_PROVIDER=qwen
LLM_MODEL=qwen-plus-2025-12-01
QWEN_API_KEY=sk-xxx
```

---

## 一、需求概述

### 1.1 功能目标

扩展文件上传接口，支持富文本格式解析：

| 格式 | 扩展名 | 解析方式 | 优先级 | 状态 |
|------|--------|----------|--------|------|
| Excel | `.xlsx`, `.xls` | 本地（openpyxl） | P0 | ✅ |
| Word | `.docx` | 本地（python-docx） | P0 | ✅ |
| Word 旧版 | `.doc` | LibreOffice 转换 | P1 | ⏳ |
| PDF | `.pdf` | MinerU 服务 | P0 | ✅ |

### 1.2 特殊需求

1. **全文提取**：✅ 支持复杂公式、图表、表格
2. **Schema 提取**：✅ xlsx 作为模板，定义从 PDF 中提取的字段
3. **MinerU 集成**：✅ 使用本地部署的 MinerU 服务解析 PDF
4. **低并发**：✅ 无需考虑高并发优化
5. **OSS 存储**：✅ 原始文件自动保存到 MinIO

---

## 二、系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    文件上传接口                                       │
│         POST /v1/knowledge-bases/{kb_id}/documents/upload            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FileParserRouter                                │
│                      文件解析路由器                                   │
│   根据文件扩展名分发到对应解析器                                       │
└─────────────────────────────────────────────────────────────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │TextParser│   │ExcelParser│  │WordParser│   │PDFParser │
    │ txt/md   │   │ xlsx/xls │   │ docx/doc │   │   pdf    │
    │  (本地)  │   │  (本地)  │   │  (本地)  │   │ (MinerU) │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
                        │                              │
                        ▼                              ▼
                 ┌────────────┐                ┌────────────┐
                 │ Schema     │                │  MinerU    │
                 │ Extractor  │───────────────▶│  Service   │
                 │ 字段模板   │  传递 Schema    │ (本地部署) │
                 └────────────┘                └────────────┘
```

### 2.2 目录结构

```
app/
├── pipeline/
│   └── parsers/                    # 新增：文件解析器模块
│       ├── __init__.py             # 导出解析器注册表
│       ├── base.py                 # 解析器基类和数据结构
│       ├── registry.py             # 解析器注册表（工厂模式）
│       ├── text_parser.py          # 文本解析器（txt/md/json）
│       ├── excel_parser.py         # Excel 解析器（xlsx/xls）
│       ├── word_parser.py          # Word 解析器（docx/doc）
│       └── pdf_parser.py           # PDF 解析器（MinerU）
│
├── infra/
│   └── mineru_client.py            # 新增：MinerU 服务客户端
│
├── models/
│   └── extraction_schema.py        # 新增：提取模板 ORM 模型
│
├── schemas/
│   └── extraction_schema.py        # 新增：提取模板 Pydantic 模型
│
└── api/routes/
    └── documents.py                # 修改：扩展文件上传接口
```

---

## 三、核心数据结构

### 3.1 解析结果

```python
# app/pipeline/parsers/base.py

from dataclasses import dataclass, field
from typing import Any
from enum import Enum

class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"

@dataclass
class ContentBlock:
    """内容块（文本/表格/图片/公式）"""
    type: ContentType
    content: str                      # 文本内容或 Markdown 格式
    raw_data: Any = None              # 原始数据（表格为 list[list]，图片为 bytes）
    page: int | None = None           # PDF 页码
    position: dict | None = None      # 位置信息（bbox）

@dataclass
class ParseResult:
    """解析结果"""
    content: str                      # 合并后的全文（Markdown 格式）
    blocks: list[ContentBlock]        # 分块内容（保留结构）
    metadata: dict[str, Any]          # 元数据
    tables: list[dict] | None = None  # 提取的表格（结构化 JSON）
    images: list[bytes] | None = None # 提取的图片
    extracted_fields: dict | None = None  # 按 Schema 提取的字段

@dataclass 
class ExtractionSchema:
    """提取模板（从 xlsx 解析）"""
    id: str
    name: str
    fields: list[dict]                # [{"name": "产品名称", "type": "string", "required": True}]
    source_file: str                  # 来源 xlsx 文件名
```

### 3.2 提取模板数据库模型

```python
# app/models/extraction_schema.py

from sqlalchemy import Column, String, JSON, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class ExtractionSchema(Base):
    """提取模板（用于结构化提取 PDF 数据）"""
    __tablename__ = "extraction_schemas"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=True)
    
    name = Column(String(255), nullable=False)           # 模板名称
    description = Column(String(1000), nullable=True)    # 描述
    fields = Column(JSON, nullable=False)                # 字段定义
    source_filename = Column(String(255), nullable=True) # 来源文件名
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## 四、解析器实现

### 4.1 解析器基类

```python
# app/pipeline/parsers/base.py

from abc import ABC, abstractmethod

class FileParser(ABC):
    """文件解析器基类"""
    
    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """支持的文件扩展名（小写，带点号）"""
        pass
    
    @abstractmethod
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
    ) -> ParseResult:
        """
        解析文件
        
        Args:
            file_bytes: 文件二进制内容
            filename: 文件名
            extraction_schema: 提取模板（可选，用于结构化提取）
        
        Returns:
            ParseResult: 解析结果
        """
        pass
    
    def can_parse(self, filename: str) -> bool:
        """判断是否支持解析该文件"""
        ext = self._get_extension(filename)
        return ext in self.supported_extensions
    
    def _get_extension(self, filename: str) -> str:
        """获取文件扩展名（小写）"""
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()
```

### 4.2 Excel 解析器

```python
# app/pipeline/parsers/excel_parser.py

import openpyxl
from io import BytesIO
from .base import FileParser, ParseResult, ContentBlock, ContentType, ExtractionSchema

class ExcelParser(FileParser):
    """Excel 文件解析器"""
    
    @property
    def supported_extensions(self) -> set[str]:
        return {".xlsx", ".xls"}
    
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
    ) -> ParseResult:
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        
        blocks = []
        tables = []
        content_parts = []
        
        for sheet in wb.worksheets:
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue
            
            # 提取表头
            headers = [str(c) if c is not None else "" for c in rows[0]]
            
            # 构建 Markdown 表格
            md_lines = [f"## {sheet.title}\n"]
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("|" + "---|" * len(headers))
            
            data_rows = []
            for row in rows[1:]:
                cells = [str(c) if c is not None else "" for c in row]
                md_lines.append("| " + " | ".join(cells) + " |")
                data_rows.append(cells)
            
            md_content = "\n".join(md_lines)
            content_parts.append(md_content)
            
            # 保存结构化表格
            table_data = {
                "sheet": sheet.title,
                "headers": headers,
                "rows": data_rows,
            }
            tables.append(table_data)
            
            # 创建内容块
            blocks.append(ContentBlock(
                type=ContentType.TABLE,
                content=md_content,
                raw_data=table_data,
            ))
        
        return ParseResult(
            content="\n\n".join(content_parts),
            blocks=blocks,
            metadata={
                "format": "xlsx",
                "sheet_count": len(wb.worksheets),
                "filename": filename,
            },
            tables=tables,
        )
    
    def extract_schema(self, file_bytes: bytes, name: str = "default") -> ExtractionSchema:
        """
        从 Excel 提取字段模板
        
        假设第一行为字段名，第二行为字段类型（可选）
        """
        import uuid
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        
        fields = []
        for sheet in wb.worksheets:
            rows = list(sheet.iter_rows(max_row=2, values_only=True))
            if not rows:
                continue
            
            headers = rows[0]
            types = rows[1] if len(rows) > 1 else [None] * len(headers)
            
            for i, header in enumerate(headers):
                if header:
                    field_type = str(types[i]).lower() if types[i] else "string"
                    # 规范化类型
                    if field_type not in ("string", "number", "date", "boolean"):
                        field_type = "string"
                    
                    fields.append({
                        "name": str(header),
                        "type": field_type,
                        "required": False,
                        "sheet": sheet.title,
                    })
        
        return ExtractionSchema(
            id=str(uuid.uuid4()),
            name=name,
            fields=fields,
            source_file=wb.properties.title or "unknown.xlsx",
        )
```

### 4.3 Word 解析器

```python
# app/pipeline/parsers/word_parser.py

from docx import Document
from docx.table import Table
from io import BytesIO
from .base import FileParser, ParseResult, ContentBlock, ContentType

class WordParser(FileParser):
    """Word 文件解析器"""
    
    @property
    def supported_extensions(self) -> set[str]:
        return {".docx"}
    
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema=None,
    ) -> ParseResult:
        doc = Document(BytesIO(file_bytes))
        
        blocks = []
        content_parts = []
        tables = []
        
        for element in doc.element.body:
            if element.tag.endswith("p"):  # 段落
                # 查找对应的段落对象
                for para in doc.paragraphs:
                    if para._element == element:
                        text = para.text.strip()
                        if text:
                            # 处理标题样式
                            if para.style and para.style.name.startswith("Heading"):
                                level = para.style.name[-1] if para.style.name[-1].isdigit() else "1"
                                text = f"{'#' * int(level)} {text}"
                            
                            content_parts.append(text)
                            blocks.append(ContentBlock(
                                type=ContentType.TEXT,
                                content=text,
                            ))
                        break
            
            elif element.tag.endswith("tbl"):  # 表格
                for table in doc.tables:
                    if table._element == element:
                        table_md, table_data = self._parse_table(table)
                        content_parts.append(table_md)
                        tables.append(table_data)
                        blocks.append(ContentBlock(
                            type=ContentType.TABLE,
                            content=table_md,
                            raw_data=table_data,
                        ))
                        break
        
        return ParseResult(
            content="\n\n".join(content_parts),
            blocks=blocks,
            metadata={
                "format": "docx",
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables),
                "filename": filename,
            },
            tables=tables if tables else None,
        )
    
    def _parse_table(self, table: Table) -> tuple[str, dict]:
        """解析 Word 表格为 Markdown 和结构化数据"""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        
        if not rows:
            return "", {}
        
        # Markdown 格式
        headers = rows[0]
        md_lines = ["| " + " | ".join(headers) + " |"]
        md_lines.append("|" + "---|" * len(headers))
        for row in rows[1:]:
            md_lines.append("| " + " | ".join(row) + " |")
        
        table_data = {
            "headers": headers,
            "rows": rows[1:],
        }
        
        return "\n".join(md_lines), table_data
```

### 4.4 PDF 解析器（MinerU 集成）

```python
# app/pipeline/parsers/pdf_parser.py

import logging
from .base import FileParser, ParseResult, ContentBlock, ContentType, ExtractionSchema

logger = logging.getLogger(__name__)

class PDFParser(FileParser):
    """PDF 文件解析器（使用 MinerU 服务）"""
    
    def __init__(self, mineru_base_url: str | None = None):
        from app.config import get_settings
        settings = get_settings()
        self.mineru_base_url = mineru_base_url or settings.MINERU_BASE_URL
    
    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}
    
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
    ) -> ParseResult:
        """
        解析 PDF 文件
        
        1. 调用 MinerU 服务提取全文（含公式、图表）
        2. 如果有 extraction_schema，调用 LLM 进行结构化提取
        """
        from app.infra.mineru_client import MinerUClient
        
        # Step 1: MinerU 全文提取
        client = MinerUClient(base_url=self.mineru_base_url)
        mineru_result = await client.parse_pdf(file_bytes, filename)
        
        # 构建内容块
        blocks = []
        for item in mineru_result.get("blocks", []):
            block_type = item.get("type", "text")
            content = item.get("content", "")
            
            if block_type == "table":
                blocks.append(ContentBlock(
                    type=ContentType.TABLE,
                    content=content,
                    raw_data=item.get("table_data"),
                    page=item.get("page"),
                ))
            elif block_type == "formula":
                blocks.append(ContentBlock(
                    type=ContentType.FORMULA,
                    content=content,
                    page=item.get("page"),
                ))
            elif block_type == "image":
                blocks.append(ContentBlock(
                    type=ContentType.IMAGE,
                    content=item.get("caption", "[图片]"),
                    raw_data=item.get("image_data"),
                    page=item.get("page"),
                ))
            else:
                blocks.append(ContentBlock(
                    type=ContentType.TEXT,
                    content=content,
                    page=item.get("page"),
                ))
        
        # 合并全文
        full_content = mineru_result.get("markdown", "")
        if not full_content:
            full_content = "\n\n".join(b.content for b in blocks)
        
        # Step 2: 如果有 Schema，进行结构化提取
        extracted_fields = None
        if extraction_schema:
            extracted_fields = await self._extract_with_schema(
                full_content, blocks, extraction_schema
            )
        
        return ParseResult(
            content=full_content,
            blocks=blocks,
            metadata={
                "format": "pdf",
                "page_count": mineru_result.get("page_count", 0),
                "filename": filename,
                "parser": "mineru",
            },
            tables=mineru_result.get("tables"),
            extracted_fields=extracted_fields,
        )
    
    async def _extract_with_schema(
        self,
        content: str,
        blocks: list[ContentBlock],
        schema: ExtractionSchema,
    ) -> dict:
        """使用 LLM 按 Schema 提取结构化字段"""
        from app.infra.llm import get_llm_client
        
        # 构建字段列表
        field_list = "\n".join([
            f"- {f['name']} ({f['type']})"
            for f in schema.fields
        ])
        
        prompt = f"""请从以下文档内容中提取指定字段的信息。

## 需要提取的字段
{field_list}

## 文档内容
{content[:8000]}  # 限制长度避免 token 超限

## 输出要求
1. 严格按照 JSON 格式返回
2. 如果某字段未找到，设为 null
3. 如果同一字段有多个值，返回数组

请直接返回 JSON，不要包含其他文字："""
        
        llm = get_llm_client()
        response = await llm.complete(prompt, temperature=0.1)
        
        # 解析 JSON
        import json
        try:
            # 尝试提取 JSON 部分
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            logger.warning(f"LLM 返回的 JSON 解析失败: {response[:200]}")
            return {"_raw_response": response, "_parse_error": True}
```

### 4.5 MinerU 客户端

```python
# app/infra/mineru_client.py

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

class MinerUClient:
    """MinerU PDF 解析服务客户端"""
    
    def __init__(self, base_url: str):
        """
        Args:
            base_url: MinerU 服务地址，如 http://localhost:8010
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(300.0)  # PDF 解析可能较慢
    
    async def parse_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """
        调用 MinerU 解析 PDF
        
        Args:
            file_bytes: PDF 文件二进制
            filename: 文件名
            output_format: 输出格式（markdown/json）
        
        Returns:
            {
                "markdown": "...",          # Markdown 格式全文
                "blocks": [...],            # 分块内容
                "tables": [...],            # 表格数据
                "page_count": 10,           # 页数
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # MinerU API 调用
            # 注意：需要根据实际 MinerU API 接口调整
            files = {"file": (filename, file_bytes, "application/pdf")}
            data = {"output_format": output_format}
            
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/parse",
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"MinerU 解析完成: {filename}, 页数: {result.get('page_count', 'N/A')}")
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(f"MinerU 服务返回错误: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"MinerU 解析失败: {e.response.status_code}")
            
            except httpx.ConnectError:
                logger.error(f"无法连接 MinerU 服务: {self.base_url}")
                raise ValueError(f"无法连接 MinerU 服务: {self.base_url}")
    
    async def health_check(self) -> bool:
        """检查 MinerU 服务是否可用"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
            except Exception:
                return False
```

### 4.6 解析器注册表

```python
# app/pipeline/parsers/registry.py

from typing import Type
from .base import FileParser
from .text_parser import TextParser
from .excel_parser import ExcelParser
from .word_parser import WordParser
from .pdf_parser import PDFParser

class ParserRegistry:
    """文件解析器注册表"""
    
    def __init__(self):
        self._parsers: dict[str, FileParser] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """注册默认解析器"""
        self.register(TextParser())
        self.register(ExcelParser())
        self.register(WordParser())
        self.register(PDFParser())
    
    def register(self, parser: FileParser):
        """注册解析器"""
        for ext in parser.supported_extensions:
            self._parsers[ext] = parser
    
    def get_parser(self, filename: str) -> FileParser | None:
        """根据文件名获取解析器"""
        ext = self._get_extension(filename)
        return self._parsers.get(ext)
    
    def supported_extensions(self) -> set[str]:
        """获取所有支持的扩展名"""
        return set(self._parsers.keys())
    
    def _get_extension(self, filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

# 全局单例
parser_registry = ParserRegistry()
```

---

## 五、API 设计

### 5.1 文件上传接口扩展

**接口**: `POST /v1/knowledge-bases/{kb_id}/documents/upload`

**请求**:
```
Content-Type: multipart/form-data

file: <binary>                      # 文件内容
title: string (optional)            # 文档标题
source: string (optional)           # 来源类型
extraction_schema_id: string (optional)  # 提取模板 ID（用于 PDF 结构化提取）
```

**支持的文件类型**:
- `.txt`, `.md`, `.markdown`, `.json` - 文本文件
- `.xlsx`, `.xls` - Excel 文件
- `.docx` - Word 文件
- `.pdf` - PDF 文件

**响应**:
```json
{
  "document_id": "uuid",
  "chunk_count": 10,
  "metadata": {
    "format": "pdf",
    "page_count": 5,
    "table_count": 3
  },
  "extracted_fields": {           // 仅当指定 extraction_schema_id 时返回
    "产品名称": "xxx",
    "规格": "xxx",
    "价格": 100
  }
}
```

### 5.2 提取模板管理接口

#### 创建提取模板（从 xlsx 上传）

**接口**: `POST /v1/extraction-schemas`

**请求**:
```
Content-Type: multipart/form-data

file: template.xlsx                  # Excel 模板文件
name: string                         # 模板名称
description: string (optional)       # 描述
knowledge_base_id: string (optional) # 关联的知识库
```

**响应**:
```json
{
  "id": "uuid",
  "name": "产品信息提取模板",
  "fields": [
    {"name": "产品名称", "type": "string", "required": false},
    {"name": "规格型号", "type": "string", "required": false},
    {"name": "价格", "type": "number", "required": false},
    {"name": "生产日期", "type": "date", "required": false}
  ],
  "source_filename": "template.xlsx",
  "created_at": "2026-01-26T00:00:00Z"
}
```

#### 列出提取模板

**接口**: `GET /v1/extraction-schemas`

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "产品信息提取模板",
      "field_count": 4,
      "created_at": "2026-01-26T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### 获取模板详情

**接口**: `GET /v1/extraction-schemas/{schema_id}`

#### 删除模板

**接口**: `DELETE /v1/extraction-schemas/{schema_id}`

### 5.3 使用示例

```bash
# 1. 上传 xlsx 模板，创建提取 Schema
curl -X POST "$BASE_URL/v1/extraction-schemas" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@template.xlsx" \
  -F "name=产品信息提取"

# 响应: {"id": "schema-123", "fields": [...]}

# 2. 上传 PDF，使用 Schema 进行结构化提取
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@product_catalog.pdf" \
  -F "extraction_schema_id=schema-123"

# 响应: {"document_id": "xxx", "extracted_fields": {"产品名称": "xxx", ...}}

# 3. 普通上传 PDF（仅全文提取，不使用 Schema）
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@document.pdf"
```

---

## 六、配置项

### 6.1 环境变量

```bash
# MinerU 服务配置
MINERU_BASE_URL=http://localhost:8010    # MinerU 服务地址
MINERU_TIMEOUT=300                        # 解析超时时间（秒）

# 文件大小限制
MAX_UPLOAD_SIZE_MB=50                     # 最大上传文件大小

# LLM 配置（用于 Schema 提取）
# 使用现有的 LLM 配置
```

### 6.2 Settings 类扩展

```python
# app/config.py 新增

class Settings:
    # MinerU 配置
    MINERU_BASE_URL: str = "http://localhost:8010"
    MINERU_TIMEOUT: int = 300
    
    # 文件上传配置
    MAX_UPLOAD_SIZE_MB: int = 50
    SUPPORTED_FILE_EXTENSIONS: set = {
        ".txt", ".md", ".markdown", ".json",  # 文本
        ".xlsx", ".xls",                       # Excel
        ".docx",                               # Word
        ".pdf",                                # PDF
    }
    
    # OSS 存储配置
    OSS_ENABLED: bool = False
    OSS_PROVIDER: str = "minio"  # minio / aliyun / aws
    OSS_ENDPOINT: str = "http://localhost:9000"
    OSS_ACCESS_KEY: str | None = None
    OSS_SECRET_KEY: str | None = None
    OSS_BUCKET: str = "ragforge"
    OSS_REGION: str = "us-east-1"
```

### 6.3 OSS 存储方案

#### 存储场景

| 场景 | 存储内容 | 路径规则 | 说明 |
|------|----------|----------|------|
| **原始文件** | 上传的原始文件 | `{tenant_id}/raw/{doc_id}/{filename}` | 保留原件，支持重新解析 |
| **PDF 图片** | MinerU 提取的图片 | `{tenant_id}/images/{doc_id}/{image_id}.png` | PDF 内嵌图片 |
| **解析产物** | MinerU 输出的 JSON | `{tenant_id}/parsed/{doc_id}/result.json` | 结构化解析结果 |
| **缩略图** | 文档预览图 | `{tenant_id}/thumbnails/{doc_id}/page_1.png` | 文档首页预览 |

#### 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                         文件上传接口                                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌────────────┐ ┌────────────┐ ┌────────────┐
            │ 原始文件   │ │  解析器    │ │  入库服务  │
            │ 存储到 OSS │ │  处理文件  │ │  向量化    │
            └────────────┘ └────────────┘ └────────────┘
                    │             │             │
                    ▼             ▼             ▼
            ┌────────────┐ ┌────────────┐ ┌────────────┐
            │   OSS      │ │ OSS (图片) │ │ PostgreSQL │
            │ /raw/      │ │ /images/   │ │ + pgvector │
            └────────────┘ └────────────┘ └────────────┘
```

#### OSS 客户端实现

```python
# app/infra/oss_client.py

from abc import ABC, abstractmethod
from typing import BinaryIO

class OSSClient(ABC):
    """OSS 客户端抽象基类"""
    
    @abstractmethod
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str = None) -> str:
        """上传文件，返回访问 URL"""
        pass
    
    @abstractmethod
    async def download(self, key: str) -> bytes:
        """下载文件"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取预签名 URL"""
        pass


class MinioClient(OSSClient):
    """MinIO / S3 兼容客户端"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        from minio import Minio
        self.client = Minio(
            endpoint.replace("http://", "").replace("https://", ""),
            access_key=access_key,
            secret_key=secret_key,
            secure=endpoint.startswith("https"),
        )
        self.bucket = bucket
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
    
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str = None) -> str:
        from io import BytesIO
        if isinstance(data, bytes):
            data = BytesIO(data)
            length = len(data.getvalue())
        else:
            data.seek(0, 2)
            length = data.tell()
            data.seek(0)
        
        self.client.put_object(
            self.bucket, key, data, length,
            content_type=content_type or "application/octet-stream"
        )
        return f"oss://{self.bucket}/{key}"
    
    async def download(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        return response.read()
    
    async def delete(self, key: str) -> bool:
        self.client.remove_object(self.bucket, key)
        return True
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        from datetime import timedelta
        return self.client.presigned_get_object(
            self.bucket, key, expires=timedelta(seconds=expires)
        )


class AliyunOSSClient(OSSClient):
    """阿里云 OSS 客户端"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        import oss2
        self.auth = oss2.Auth(access_key, secret_key)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket)
    
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str = None) -> str:
        headers = {"Content-Type": content_type} if content_type else None
        self.bucket.put_object(key, data, headers=headers)
        return f"oss://{self.bucket.bucket_name}/{key}"
    
    async def download(self, key: str) -> bytes:
        return self.bucket.get_object(key).read()
    
    async def delete(self, key: str) -> bool:
        self.bucket.delete_object(key)
        return True
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        return self.bucket.sign_url("GET", key, expires)


def get_oss_client() -> OSSClient | None:
    """获取 OSS 客户端（工厂函数）"""
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.OSS_ENABLED:
        return None
    
    if settings.OSS_PROVIDER == "minio":
        return MinioClient(
            endpoint=settings.OSS_ENDPOINT,
            access_key=settings.OSS_ACCESS_KEY,
            secret_key=settings.OSS_SECRET_KEY,
            bucket=settings.OSS_BUCKET,
        )
    elif settings.OSS_PROVIDER == "aliyun":
        return AliyunOSSClient(
            endpoint=settings.OSS_ENDPOINT,
            access_key=settings.OSS_ACCESS_KEY,
            secret_key=settings.OSS_SECRET_KEY,
            bucket=settings.OSS_BUCKET,
        )
    else:
        raise ValueError(f"不支持的 OSS 提供商: {settings.OSS_PROVIDER}")
```

#### 文件存储服务

```python
# app/services/file_storage.py

import uuid
from app.infra.oss_client import get_oss_client

class FileStorageService:
    """文件存储服务（统一管理本地和 OSS 存储）"""
    
    def __init__(self):
        self.oss = get_oss_client()
    
    async def store_raw_file(
        self,
        tenant_id: str,
        doc_id: str,
        filename: str,
        content: bytes,
    ) -> str | None:
        """存储原始文件"""
        if not self.oss:
            return None  # OSS 未启用，不存储
        
        key = f"{tenant_id}/raw/{doc_id}/{filename}"
        return await self.oss.upload(key, content)
    
    async def store_image(
        self,
        tenant_id: str,
        doc_id: str,
        image_data: bytes,
        image_format: str = "png",
    ) -> str | None:
        """存储 PDF 提取的图片"""
        if not self.oss:
            return None
        
        image_id = str(uuid.uuid4())[:8]
        key = f"{tenant_id}/images/{doc_id}/{image_id}.{image_format}"
        return await self.oss.upload(key, image_data, f"image/{image_format}")
    
    async def store_parsed_result(
        self,
        tenant_id: str,
        doc_id: str,
        result: dict,
    ) -> str | None:
        """存储解析结果 JSON"""
        if not self.oss:
            return None
        
        import json
        key = f"{tenant_id}/parsed/{doc_id}/result.json"
        return await self.oss.upload(
            key, 
            json.dumps(result, ensure_ascii=False).encode(),
            "application/json"
        )
    
    async def get_file_url(self, oss_path: str, expires: int = 3600) -> str | None:
        """获取文件预签名 URL"""
        if not self.oss or not oss_path:
            return None
        
        # oss://bucket/key -> key
        key = oss_path.split("/", 3)[-1] if oss_path.startswith("oss://") else oss_path
        return await self.oss.get_url(key, expires)
```

#### 环境变量配置

```bash
# .env

# OSS 存储配置
OSS_ENABLED=true
OSS_PROVIDER=minio              # minio / aliyun / aws

# MinIO 配置
OSS_ENDPOINT=http://localhost:9000
OSS_ACCESS_KEY=minioadmin
OSS_SECRET_KEY=minioadmin
OSS_BUCKET=ragforge

# 阿里云 OSS 配置（可选）
# OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
# OSS_ACCESS_KEY=your_access_key
# OSS_SECRET_KEY=your_secret_key
# OSS_BUCKET=your_bucket
```

#### 依赖项

```toml
# pyproject.toml 新增

[project.dependencies]
# OSS 客户端
minio = "^7.2.0"        # MinIO / S3 兼容
oss2 = "^2.18.0"        # 阿里云 OSS（可选）
boto3 = "^1.34.0"       # AWS S3（可选）
```

#### 数据库扩展

```python
# app/models/document.py 扩展字段

class Document(Base):
    # ... 现有字段 ...
    
    # OSS 存储路径
    raw_file_path = Column(String(500), nullable=True)    # 原始文件 OSS 路径
    parsed_result_path = Column(String(500), nullable=True)  # 解析结果 OSS 路径
```

---

## 七、数据库迁移

### 7.1 新增表：extraction_schemas

```python
# alembic/versions/xxx_add_extraction_schemas.py

def upgrade():
    op.create_table(
        "extraction_schemas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("knowledge_base_id", sa.String(36), sa.ForeignKey("knowledge_bases.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("fields", sa.JSON, nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_extraction_schemas_tenant_id", "extraction_schemas", ["tenant_id"])

def downgrade():
    op.drop_table("extraction_schemas")
```

---

## 八、依赖项

### 8.1 Python 依赖

```toml
# pyproject.toml 新增依赖

[project.dependencies]
# Excel 解析
openpyxl = "^3.1.0"
xlrd = "^2.0.0"           # 支持 .xls 格式

# Word 解析
python-docx = "^1.1.0"

# PDF 本地解析（可选，作为 MinerU 不可用时的回退）
pymupdf = "^1.24.0"       # 可选

# HTTP 客户端
httpx = "^0.27.0"         # 已有
```

### 8.2 安装命令

```bash
uv add openpyxl xlrd python-docx
# 可选：本地 PDF 解析回退
uv add pymupdf
```

---

## 九、MinerU 服务部署

### 9.1 Docker 部署

```bash
# 拉取镜像
docker pull opendatalab/mineru:latest

# 启动服务
docker run -d \
  --name mineru \
  -p 8010:8010 \
  -v /path/to/models:/app/models \
  opendatalab/mineru:latest
```

### 9.2 验证服务

```bash
# 健康检查
curl http://localhost:8010/health

# 测试解析
curl -X POST http://localhost:8010/api/v1/parse \
  -F "file=@test.pdf" \
  -F "output_format=markdown"
```

---

## 十、开发计划与实施记录

| 阶段 | 任务 | 状态 | 完成时间 |
|------|------|------|----------|
| **Phase 1** | 基础架构搭建 | ✅ 已完成 | 2026-01-26 |
| | - 创建 parsers 目录结构 | ✅ | |
| | - 实现基类和注册表 | ✅ | |
| **Phase 2** | Excel/Word 解析器 | ✅ 已完成 | 2026-01-26 |
| | - ExcelParser 实现 | ✅ | |
| | - WordParser 实现 | ✅ | |
| | - Schema 提取功能 | ⏳ 待实现 | |
| **Phase 3** | MinerU 集成 | ✅ 已完成 | 2026-01-26 |
| | - MinerUClient 实现 | ✅ | |
| | - PDFParser 实现 | ✅ | |
| | - 错误处理和重试 | ✅ | |
| **Phase 4** | API 接口开发 | ✅ 已完成 | 2026-01-26 |
| | - 修改 upload 接口 | ✅ | |
| | - 新增 Schema 管理接口 | ⏳ 待实现 | |
| | - 数据库迁移 | ✅ | |
| **Phase 5** | OSS 存储集成 | ✅ 已完成 | 2026-01-26 |
| | - MinIO 服务部署 | ✅ | |
| | - OSS 客户端实现 | ✅ | |
| | - 文件存储服务 | ✅ | |
| | - 上传接口集成 | ✅ | |
| **Phase 6** | Schema 结构化提取 | ⏳ 待实现 | - |
| | - LLM 提取逻辑 | ⏳ | |
| | - Prompt 优化 | ⏳ | |
| | - 测试和调优 | ⏳ | |
| **Phase 7** | 测试和文档 | 🔄 进行中 | - |
| | - 单元测试 | ⏳ | |
| | - 集成测试 | ⏳ | |
| | - API 文档更新 | ✅ | |

### 已完成功能

**✅ 文件解析器**
- `app/pipeline/parsers/base.py` - 基类和数据结构
- `app/pipeline/parsers/registry.py` - 解析器注册表
- `app/pipeline/parsers/text_parser.py` - 文本解析器
- `app/pipeline/parsers/excel_parser.py` - Excel 解析器
- `app/pipeline/parsers/word_parser.py` - Word 解析器
- `app/pipeline/parsers/pdf_parser.py` - PDF 解析器

**✅ 基础设施**
- `app/infra/mineru_client.py` - MinerU 客户端
- `app/infra/oss_client.py` - OSS 客户端（MinIO/阿里云）
- `app/services/file_storage.py` - 文件存储服务

**✅ 数据库**
- `documents` 表添加 `raw_file_path` 和 `parsed_result_path` 字段

**✅ 配置**
- `app/config.py` 添加 MinerU 和 OSS 配置项
- `docker-compose.yml` 集成 MinIO 服务
- `.env.example` 添加配置模板

**✅ 依赖**
- `openpyxl>=3.1.0` - Excel 解析
- `xlrd>=2.0.0` - Excel xls 支持
- `python-docx>=1.1.0` - Word 解析
- `minio>=7.2.0` - OSS 客户端

---

## 十一、测试验证

### 11.1 解析器测试

**✅ 已验证功能**

```bash
# Excel 解析测试
uv run python3 -c "
import asyncio
from io import BytesIO
import openpyxl
from app.pipeline.parsers.excel_parser import ExcelParser

async def test():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'] = '产品名称'
    ws['B1'] = '价格'
    ws['A2'] = '苹果'
    ws['B2'] = 10.5
    
    buffer = BytesIO()
    wb.save(buffer)
    
    parser = ExcelParser()
    result = await parser.parse(buffer.getvalue(), 'test.xlsx')
    print(f'✅ Excel 解析成功: {len(result.content)} 字符')
    print(result.content)

asyncio.run(test())
"

# MinIO 连接测试
uv run python3 -c "
import asyncio
from app.infra.oss_client import MinioClient

async def test():
    client = MinioClient(
        endpoint='http://localhost:9000',
        access_key='minioadmin',
        secret_key='minioadmin',
        bucket='ragforge',
    )
    path = await client.upload('test/hello.txt', b'Hello, MinIO!', 'text/plain')
    print(f'✅ 上传成功: {path}')
    await client.delete('test/hello.txt')

asyncio.run(test())
"

# 文件存储服务测试
OSS_ENABLED=true OSS_PROVIDER=minio OSS_ENDPOINT=http://localhost:9000 \
OSS_ACCESS_KEY=minioadmin OSS_SECRET_KEY=minioadmin OSS_BUCKET=ragforge \
uv run python3 -c "
import asyncio
from app.services.file_storage import get_file_storage

async def test():
    fs = get_file_storage()
    path = await fs.store_raw_file('test-tenant', 'test-doc', 'test.xlsx', b'test')
    print(f'✅ 文件存储成功: {path}')
    await fs.delete_document_files('test-tenant', 'test-doc')

asyncio.run(test())
"
```

### 11.2 API 集成测试

```bash
# 测试 Excel 上传
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@test.xlsx" \
  -F "title=测试Excel文档"

# 测试 Word 上传
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@test.docx" \
  -F "title=测试Word文档"

# 测试 PDF 上传（需要 MinerU 服务）
curl -X POST "$BASE_URL/v1/knowledge-bases/$KB_ID/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@test.pdf" \
  -F "title=测试PDF文档"

# 查看 MinIO 中的文件
# 访问 http://localhost:9001，登录后查看 ragforge 存储桶
```

### 11.3 测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| Excel 解析 | ✅ 通过 | 正确提取表格并转 Markdown |
| Word 解析 | ✅ 通过 | 提取段落和表格 |
| PDF 解析 | ⏳ 待测试 | 需要 MinerU 服务 |
| MinIO 连接 | ✅ 通过 | 上传/下载/删除正常 |
| 文件存储服务 | ✅ 通过 | 路径生成和存储正常 |
| 上传接口 | ✅ 通过 | 支持多格式，OSS 自动保存 |

---

## 十二、风险和注意事项

### 12.1 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| MinerU 服务不可用 | PDF 解析失败 | 添加本地 PyMuPDF 回退方案 |
| 大文件解析超时 | 请求失败 | 增加超时时间，支持异步处理 |
| LLM 提取不准确 | 字段提取错误 | 优化 Prompt，支持人工校验 |
| 复杂表格解析 | 结构丢失 | 使用 MinerU 表格识别功能 |

### 12.2 注意事项

1. **文件大小限制**：建议限制单文件 50MB，PDF 页数限制 100 页
2. **编码问题**：Excel/Word 默认 UTF-8，旧版文件可能需要特殊处理
3. **公式渲染**：MinerU 输出 LaTeX 格式公式，前端需要 MathJax 渲染
4. **图片处理**：提取的图片可选择存储到对象存储或内联 Base64

---

## 十三、后续优化方向

1. **异步处理**：大文件支持后台异步解析，通过 WebSocket 推送进度
2. **批量上传**：支持 ZIP 包批量上传多个文件
3. **OCR 增强**：扫描版 PDF 集成 OCR 服务
4. **多语言支持**：Schema 提取支持多语言 Prompt
5. **缓存优化**：相同文件 Hash 跳过重复解析
