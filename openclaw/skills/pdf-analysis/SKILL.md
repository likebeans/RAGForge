---
name: pdf-analysis
description: 直连 RagForge 执行 PDF 分析：按产品模板提取结构化字段并导出 Excel，同时将 PDF 解析后的 Markdown 内容按 Markdown chunking 规则入库到“项目管理”知识库。
metadata: {"openclaw":{"emoji":"📄"}}
---

# pdf-analysis

当用户要求“分析 PDF”“提取 PDF 内容”“导出 Excel”“PDF 入库到项目管理知识库”时，启用本技能。

## 配置来源

读取 `{baseDir}/config.env`：

- `RAGFORGE_BASE_URL`：RagForge 服务地址，默认 `http://192.168.168.105:8020`
- `RAGFORGE_API_KEY`：RagForge API Key
- `DEFAULT_KB_ID`：默认知识库 ID，默认 `71dd8415-8a4b-4543-b6f0-8f11e3b88176`
- `DEFAULT_SCHEMA_ID`：默认提取模板 ID，默认 `fa1baff3-553d-415f-b9c0-1afd4f90eb93`

如果 `config.env` 未设置 `RAGFORGE_API_KEY`，脚本会回退读取仓库根目录 `.env` 中的 `RAGFORGE_API_KEY` 或 `RAGFORGE_ADMIN_KEY`。

## 执行目标

默认串联以下步骤：

1. 确认目标知识库使用 `markdown` chunker
2. 上传 PDF 到“项目管理”知识库，让 RagForge/MinerU 完成 `PDF -> Markdown -> Chunk -> 入库`
3. 轮询文档状态，直到入库处理完成
4. 默认使用“产品信息提取模板”做结构化提取并导出 Excel
5. 如果用户明确给出想要的字段，也按用户字段补充返回提取结果
6. 将 Excel 产出一个可供 OpenClaw 发送附件的 `delivery_media_path`
7. 如果当前是聊天通道会话，主动把 Excel 作为附件发回当前会话
8. 输出中文摘要

## 常用命令

```bash
# 列出提取模板
python3 {baseDir}/scripts/ragforge_pdf.py schemas

# 列出知识库
python3 {baseDir}/scripts/ragforge_pdf.py knowledge-bases

# 执行完整流程
python3 {baseDir}/scripts/ragforge_pdf.py run \
  --pdf /path/to/file.pdf \
  --schema-id fa1baff3-553d-415f-b9c0-1afd4f90eb93 \
  --kb-id 71dd8415-8a4b-4543-b6f0-8f11e3b88176 \
  --output /path/to/output.xlsx

# 按用户指定字段补充返回
python3 {baseDir}/scripts/ragforge_pdf.py run \
  --pdf /path/to/file.pdf \
  --field "产品定位" \
  --field "核心卖点" \
  --field "商业模式"
```

## 参数说明

- `--pdf`：PDF 文件路径，可多次指定
- `--schema-id`：提取模板 ID，未指定时使用默认产品模板
- `--kb-id`：知识库 ID，未指定时使用“项目管理”知识库
- `--output`：Excel 输出路径，未指定时默认在 PDF 同目录生成 `*_提取结果.xlsx`
- `--chunk-size` / `--chunk-overlap`：覆盖 Markdown chunker 参数
- `--field`：按用户需求补充提取的字段，可多次指定
- `--top-k`：自定义字段提取时的检索条数
- `--skip-kb-sync`：跳过知识库 chunker 配置同步
- `--skip-ingest`：只做提取和导出，不入库
- `--skip-extract`：只入库，不做结构化提取

脚本输出字段补充说明：

- `excel_output`：主导出路径
- `delivery_media_path`：OpenClaw 可安全发送附件的路径；若原始导出路径不在允许目录，脚本会自动复制到 `~/.openclaw/workspace`

## 对话内默认行为

如果用户没有额外说明：

- 默认知识库：`项目管理` (`71dd8415-8a4b-4543-b6f0-8f11e3b88176`)
- 默认提取模板：`产品信息提取模板` (`fa1baff3-553d-415f-b9c0-1afd4f90eb93`)
- 默认执行：入库 + 提取 + Excel 导出
- 如果用户点名了要看的字段，额外返回这些字段的提取结果，即使没有另传模板
- 自定义字段优先走 RagForge `rag`，若生成接口异常则自动回退 `retrieve` 返回相关 chunks 供模型整理

## 输出要求

向用户输出中文摘要，至少包含：

1. 处理了几个 PDF
2. 文档当前处理状态（是否已到 `completed`；若仍为 `pending` 但 indexed chunks 已可检索，也要明确说明“已可用”）
3. 是否已同步知识库为 Markdown chunking
4. 是否已入库到“项目管理”知识库
5. Excel 导出路径
6. 提取结果中是否有明显缺失或模板不匹配
7. Excel 是否已经作为飞书附件发出

如果当前是在 OpenClaw 的聊天会话里执行，并且脚本结果里有 `delivery_media_path`：

1. 先用 `message` 工具把 `delivery_media_path` 作为附件发送到当前会话
2. `message` 工具参数使用：
   - `action: "send"`
   - `message: "PDF 解析结果 Excel 附件"`
   - `media: <delivery_media_path>`
3. 不要只给本地文件路径，不要依赖用户点击 Markdown 文件链接
4. 最终中文摘要里要明确说明“Excel 已作为附件发送”

## 注意事项

- 这是直连 RagForge 的 skill，不再走 `pipeline` 异步任务
- RagForge 文档上传接口会先返回 `document_id`，随后异步完成分块与索引；脚本会轮询状态
- 如果 PDF 内容与“产品信息提取模板”不匹配，Excel 可能只有状态列，没有有效字段
- 同步知识库 chunker 会影响后续入库到该知识库的文档行为
- OpenClaw 发送本地附件有安全目录限制；`delivery_media_path` 就是为了解决这个限制
