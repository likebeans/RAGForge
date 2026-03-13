# Qwen Doc PDF Extraction Design

## Goal

将现有 `POST /v1/extraction-schemas/extract/qwen-plus` 从“PDF 转图片后调用 `qwen3.5-vl-plus`”替换为“直接上传 PDF 到阿里云百炼文件接口，再使用 `qwen-doc-turbo` 做固定 30 字段提取”。

该接口保留原有路由，默认字段模板保持不变，但返回结构统一补充模型、文件解析模式、远端文件标识以及标准错误信息。

## Current State

- 路由位于 `app/api/routes/extraction.py`
- 当前实现会先把 PDF 用 PyMuPDF 按页渲染成 PNG
- 再调用 `qwen3.5-vl-plus` 做多张图片理解
- 返回结果对调用方暴露较少，且模型 JSON 解析失败时会返回半成功结构

现状的问题：

- 不是真正的 PDF 直传
- 页数越多，图片体积和请求负担越大
- 错误结构不统一，调用方难以区分上游失败和模型输出异常
- 路由名与真实模型能力逐渐脱节

## Recommended Approach

保留现有路由 `POST /v1/extraction-schemas/extract/qwen-plus`，但内部实现改为：

1. 校验上传文件为 PDF 且内容非空
2. 调用 DashScope OpenAI 兼容文件接口上传文件，`purpose=file-extract`
3. 获取 `file_id`
4. 调用 `qwen-doc-turbo`，通过 `fileid://{file_id}` 让模型直接读取 PDF
5. 使用固定 30 字段提示词要求模型仅返回 JSON 数组
6. 解析模型返回，标准化成功和失败响应
7. 请求结束后尽量删除远端文件，避免文件堆积

## Alternatives Considered

### Option A: Keep the current image pipeline

优点：

- 改动最小
- 不需要引入百炼文件接口

缺点：

- 不是直传 PDF
- 多页文档成本和时延更差
- 识别链路更容易受页面渲染质量影响

结论：不采用。

### Option B: Switch to `qwen-long`

优点：

- 同样支持通过 `file_id` 理解 PDF

缺点：

- 更偏长文档理解/问答，不如 `qwen-doc-turbo` 贴合字段抽取

结论：保留为备选，不作为首选实现。

### Option C: Recommended, use `qwen-doc-turbo`

优点：

- 官方定位匹配“文档抽取、结构化输出”
- 原生支持 PDF + `file_id`
- 更接近业务目标，链路更直接

缺点：

- 需要重新组织服务层和错误处理
- 路由名保持 `qwen-plus` 会与真实模型名不完全一致

结论：采用。

## API Contract

### Request

- 路由：`POST /v1/extraction-schemas/extract/qwen-plus`
- 表单字段：
  - `file`: 单个 PDF 文件

约束：

- 仅支持 PDF
- 仅使用默认 30 字段模板
- 不支持调用方自定义字段列表

### Success Response

```json
{
  "filename": "example.pdf",
  "model": "qwen-doc-turbo",
  "file_id": "file-abc123",
  "parse_mode": "file_id",
  "page_count": null,
  "extracted_fields": [
    {
      "项目": "ND-003",
      "靶点": "GLP-1R",
      "研发机构": "示例公司"
    }
  ],
  "raw_response": {
    "content": "[...]"
  }
}
```

约定：

- `extracted_fields` 始终返回数组
- 单项目文档也返回长度为 1 的数组
- `page_count` 在直传模式下允许为 `null`
- `raw_response` 仅保留必要文本用于排障

### Error Response

```json
{
  "error": {
    "code": "MODEL_INVALID_JSON",
    "message": "模型返回内容不是合法 JSON",
    "model": "qwen-doc-turbo",
    "file_id": "file-abc123",
    "parse_mode": "file_id"
  }
}
```

错误码建议：

- `INVALID_FILE_TYPE`
- `EMPTY_FILE`
- `FILE_UPLOAD_FAILED`
- `MODEL_REQUEST_FAILED`
- `MODEL_INVALID_JSON`
- `MODEL_INVALID_PAYLOAD`
- `INTERNAL_ERROR`

## Architecture

建议新增一个独立服务模块，例如 `app/services/qwen_doc_extraction.py`，负责：

- 解析租户级/环境级 Qwen Provider 配置
- 生成固定 30 字段抽取提示词
- 调用 DashScope 文件上传接口
- 调用 `qwen-doc-turbo`
- 解析和清洗模型返回
- 尝试删除远端文件

路由层只保留：

- 输入校验
- 调用服务
- 将不同错误映射为 `HTTPException`
- 返回统一响应结构

这样可以避免把外部接口细节和 JSON 解析逻辑继续堆在路由文件里，也更利于单元测试。

## Prompt Strategy

提示词需要强约束：

- 明确要提取默认 30 字段
- 要求提取文档中的所有项目
- 未提及字段统一填 `"未提及"`
- 仅允许输出 JSON 数组
- 不允许解释文字、代码块或额外说明

如果模型仍然返回代码块包裹的 JSON，服务层可以做一次兼容剥离；如果剥离后仍然不是合法 JSON，则按 `422` 返回结构化错误。
当前实现不依赖 `response_format`，而是使用强约束提示词配合服务层解析，以避免数组输出和 `json_object` 模式之间的语义冲突。

## Error Handling

- 文件校验失败：`400`
- 百炼文件上传失败：`502`
- 模型调用失败：`502`
- 模型返回非 JSON 或缺少必需结构：`422`
- 未知异常：`500`

补充策略：

- 上传成功后，无论主流程成功或失败，都尽量删除远端文件
- 删除失败仅记日志，不影响主响应
- 日志需要带 `filename`、`model`、`file_id`

## Testing Strategy

### Unit Tests

新增针对服务模块的测试，覆盖：

- 默认提示词包含固定字段和数组输出要求
- 成功上传文件并返回合法 JSON 数组
- 模型返回 fenced JSON 时可正常剥离
- 模型返回非法 JSON 时抛出结构化异常
- 文件上传异常和模型调用异常的映射
- 删除远端文件失败不影响主流程

### Route Tests

新增针对路由的测试，覆盖：

- 非 PDF 请求返回 `400`
- 空文件返回 `400`
- 正常请求返回标准字段：`model`、`file_id`、`parse_mode`、`extracted_fields`
- 服务抛出 JSON 错误时路由返回 `422`
- 服务抛出上游错误时路由返回 `502`

### Existing Tests

保留现有 `tests/test_extraction_api.py` 作为 e2e 参考，不直接依赖真实百炼环境。

## Open Questions Resolved

- 是否保留旧路由：保留
- 是否继续使用默认 30 字段：是
- 是否允许补充标准化返回字段：允许
- 是否在当前工作区直接改动：是

## Implementation Notes

- 需要确认当前 `openai` SDK 在 DashScope 兼容模式下支持 `files.create` / `files.delete`
- 路由名虽然仍是 `qwen-plus`，但返回 `model=qwen-doc-turbo`，避免误导调用方
- 如果后续需要彻底纠正命名，可在后续版本补一个别名路由并逐步弃用旧名称
