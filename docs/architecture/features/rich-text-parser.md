# 富文本解析器设计

## 1. 简介
富文本解析器（Rich Text Parser）是 RAGForge 的核心组件之一，负责将上传的复杂文档（PDF、Word、Excel、PPT、HTML 等）转换为统一的 Markdown 格式，以便进行切分和向量化。

## 2. 核心功能

### 2.1 多格式支持
- **PDF**: 使用 `pdfplumber` 或 `PyMuPDF` 提取文本和表格。
- **Word (DOCX)**: 使用 `python-docx` 提取段落、表格和图片占位符。
- **Excel (XLSX)**: 将表格转换为 Markdown 表格格式。
- **PPT (PPTX)**: 提取幻灯片文本和备注。
- **HTML/Markdown**: 清洗和标准化。

### 2.2 结构化提取
- **标题识别**: 自动识别文档层级结构（H1-H6）。
- **表格处理**: 将表格转换为标准 Markdown 表格，保留行列结构。
- **列表处理**: 识别有序和无序列表。
- **代码块**: 识别并保留代码块格式。

### 2.3 清洗与标准化
- 去除多余的空行和空白字符。
- 统一标点符号。
- 处理特殊字符编码。

## 3. 架构设计

```mermaid
graph TD
    A[输入文件] --> B{文件类型判定}
    B -->|PDF| C[PDF Parser]
    B -->|DOCX| D[Word Parser]
    B -->|XLSX| E[Excel Parser]
    B -->|PPTX| F[PPT Parser]
    B -->|HTML| G[HTML Parser]
    C --> H[中间格式 (Elements)]
    D --> H
    E --> H
    F --> H
    G --> H
    H --> I[Markdown Generator]
    I --> J[输出 Markdown]
```

## 4. 接口定义

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> str:
        """
        解析文件并返回 Markdown 内容
        """
        pass

class RichTextParser:
    def parse(self, file_path: str, mime_type: str = None) -> str:
        """
        根据文件类型分发到具体的 Parser
        """
        pass
```

## 5. 配置选项
- `ocr_enabled`: 是否启用 OCR（针对扫描版 PDF）。
- `table_processing`: 表格处理模式（markdown/csv/html）。
- `image_extraction`: 是否提取图片。

## 6. 未来规划
- 集成 OCR 引擎（如 PaddleOCR）处理图片和扫描件。
- 支持更多格式（如 EPub、Mobi）。
- 增强对复杂表格和公式的识别。
