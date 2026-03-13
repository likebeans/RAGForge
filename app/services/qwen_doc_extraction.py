import asyncio
import contextlib
import json
import logging
import re
from typing import Any, cast

import fitz  # type: ignore[import-untyped]
from openai import AsyncOpenAI

from app.pipeline.parsers.pdf_parser import DEFAULT_EXTRACTION_FIELDS

logger = logging.getLogger(__name__)

DEFAULT_QWEN_DOC_MODEL = "qwen-doc-turbo"
DEFAULT_PARSE_MODE = "file_id"
PROJECT_ID_PATTERN = re.compile(r"\b([A-Z]{2,10})[-_ ]?(\d{3,4})\b")


class QwenDocExtractionError(Exception):
    """Qwen 文档抽取异常。"""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        file_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.file_id = file_id


def build_default_extraction_prompt() -> str:
    """构建默认 30 字段抽取提示词。"""
    field_list = "\n".join(f"- {field['name']}" for field in DEFAULT_EXTRACTION_FIELDS)
    return f"""请从 PDF 中提取所有项目的完整信息。

需要提取的字段：
{field_list}

要求：
1. 必须提取文档中所有项目
2. 未提及字段统一填写"未提及"
3. 只允许返回 JSON数组
4. 每个数组元素必须是一个项目对象
5. 不要输出解释文字或额外说明
"""


def build_project_list_prompt() -> str:
    """构建项目列表抽取提示词。"""
    return """请先识别文档中出现的所有项目编号。

要求：
1. 提取所有项目，不要遗漏
2. 项目编号示例：ND-003、ND003、XY-001
3. 去重后按文档出现顺序返回
4. 只允许返回 JSON数组
5. 数组元素只包含项目编号字符串，示例：["ND-003", "ND-004"]
6. 不要返回任何解释文字
"""


def build_project_prompt(project_id: str) -> str:
    """构建单项目字段抽取提示词。"""
    field_list = "\n".join(f"- {field['name']}" for field in DEFAULT_EXTRACTION_FIELDS)
    return f"""请只提取项目 {project_id} 的信息，不要混入其他项目。

需要提取的字段：
{field_list}

要求：
1. 只提取该项目，不要混入其他项目
2. 如果字段无法明确归属到该项目，填写"未提及"
3. "项目"字段必须返回 "{project_id}"
4. 只允许返回 JSON对象，不要返回数组
5. 不要输出解释文字或额外说明
"""


def build_document_summary_prompt() -> str:
    """构建整份 PDF 摘要提示词。"""
    return """请基于整个PDF内容，给出一段简要介绍。

要求：
1. 概括公司/主体、核心技术或主题、主要项目管线或业务重点、阶段或合作融资信息
2. 用中文输出
3. 控制在3-5句话内
4. 不要分点，不要输出JSON
"""


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if "```json" in stripped:
        return stripped.split("```json", 1)[1].split("```", 1)[0].strip()
    if stripped.startswith("```") and "```" in stripped[3:]:
        return stripped.split("```", 1)[1].split("```", 1)[0].strip()
    return stripped


def _normalize_project_id(value: str) -> str:
    """规范化项目编号格式。"""
    candidate = re.sub(r"\s+", "", value).upper()
    match = PROJECT_ID_PATTERN.search(candidate)
    if not match:
        return candidate

    prefix = match.group(1)
    digits = match.group(2).zfill(3)
    return f"{prefix}-{digits}"


def _maybe_project_id(value: str) -> str | None:
    """尝试将字符串解析为项目编号。"""
    candidate = re.sub(r"\s+", "", value).upper()
    if not PROJECT_ID_PATTERN.search(candidate):
        return None
    return _normalize_project_id(candidate)


def parse_project_ids(content: str) -> list[str]:
    """解析模型返回的项目编号列表。"""
    cleaned = _strip_code_fence(content)
    payload = json.loads(cleaned)

    if isinstance(payload, dict):
        payload = payload.get("items") or payload.get("projects") or [payload]

    if not isinstance(payload, list):
        raise ValueError("模型返回的项目列表不是数组")

    results: list[str] = []
    seen: set[str] = set()

    for item in payload:
        raw_value: str | None = None
        if isinstance(item, str):
            raw_value = item
        elif isinstance(item, dict):
            for key in ("项目", "project_id", "id", "name"):
                value = item.get(key)
                if isinstance(value, str):
                    raw_value = value
                    break

        if not raw_value:
            continue

        normalized = _maybe_project_id(raw_value)
        if not normalized:
            continue

        if normalized not in seen:
            seen.add(normalized)
            results.append(normalized)

    return results


def extract_project_ids_from_text(text: str) -> list[str]:
    """从本地抽取文本中提取项目编号。"""
    results: list[str] = []
    seen: set[str] = set()

    for match in PROJECT_ID_PATTERN.finditer(text.upper()):
        normalized = _normalize_project_id(match.group(0))
        if normalized not in seen:
            seen.add(normalized)
            results.append(normalized)

    return results


def extract_project_ids_from_pdf_bytes(file_bytes: bytes) -> list[str]:
    """从 PDF 文本层提取项目编号。"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        text = "\n".join(doc.load_page(i).get_text("text") for i in range(len(doc)))
    finally:
        doc.close()

    return extract_project_ids_from_text(text)


def parse_extracted_fields(content: str) -> list[dict[str, Any]]:
    """解析模型返回的结构化字段。"""
    cleaned = _strip_code_fence(content)
    payload = json.loads(cleaned)

    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload

    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list) and all(isinstance(item, dict) for item in items):
            return items
        return [payload]

    raise ValueError("模型返回的 JSON 结构不是对象或对象数组")


async def _request_file_completion(
    client: AsyncOpenAI,
    *,
    model: str,
    file_id: str,
    prompt: str,
) -> str:
    """基于 file_id 发起一次抽取请求。"""
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"fileid://{file_id}"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def _filter_project_ids(
    model_project_ids: list[str],
    text_project_ids: list[str],
) -> list[str]:
    """使用本地文本抽取结果过滤模型返回的噪音项目编号。"""
    if not text_project_ids:
        return model_project_ids

    allowed = set(text_project_ids)
    return [project_id for project_id in model_project_ids if project_id in allowed]


def _select_project_payload(
    project_id: str,
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """从候选 payload 中选出当前项目。"""
    normalized_target = _normalize_project_id(project_id)
    for item in payloads:
        project_value = item.get("项目")
        if isinstance(project_value, str) and _normalize_project_id(project_value) == normalized_target:
            item["项目"] = normalized_target
            return item

    if payloads:
        payloads[0]["项目"] = normalized_target
        return payloads[0]

    return {"项目": normalized_target}


def _extract_project_ids_from_payloads(payloads: list[dict[str, Any]]) -> list[str]:
    """从抽取结果中归一化提取项目编号。"""
    results: list[str] = []
    seen: set[str] = set()

    for item in payloads:
        raw_value = item.get("项目")
        if not isinstance(raw_value, str):
            continue

        normalized = _maybe_project_id(raw_value)
        if not normalized:
            continue

        item["项目"] = normalized
        if normalized not in seen:
            seen.add(normalized)
            results.append(normalized)

    return results


async def _extract_fields_via_project_fallback(
    client: AsyncOpenAI,
    *,
    model: str,
    file_id: str,
    file_bytes: bytes,
) -> tuple[str, list[str], list[dict[str, Any]], list[dict[str, str]]]:
    """旧的项目列表 + 逐项目抽取回退逻辑。"""
    project_list_content = await _request_file_completion(
        client,
        model=model,
        file_id=file_id,
        prompt=build_project_list_prompt(),
    )
    project_ids = parse_project_ids(project_list_content)
    text_project_ids = extract_project_ids_from_pdf_bytes(file_bytes)
    project_ids = _filter_project_ids(project_ids, text_project_ids)

    project_responses: list[dict[str, str]] = []
    extracted_fields: list[dict[str, Any]] = []

    if not project_ids:
        fallback_content = await _request_file_completion(
            client,
            model=model,
            file_id=file_id,
            prompt=build_default_extraction_prompt(),
        )
        extracted_fields = parse_extracted_fields(fallback_content)
        project_ids = _extract_project_ids_from_payloads(extracted_fields)
        project_responses.append(
            {"project_id": "fallback", "content": fallback_content}
        )
        return project_list_content, project_ids, extracted_fields, project_responses

    for project_id in project_ids:
        project_content = await _request_file_completion(
            client,
            model=model,
            file_id=file_id,
            prompt=build_project_prompt(project_id),
        )
        payloads = parse_extracted_fields(project_content)
        extracted_fields.append(_select_project_payload(project_id, payloads))
        project_responses.append(
            {"project_id": project_id, "content": project_content}
        )

    return project_list_content, project_ids, extracted_fields, project_responses


async def _safe_delete_remote_file(client: AsyncOpenAI, file_id: str | None) -> None:
    """尽力删除远端文件，不影响主流程。"""
    if not file_id:
        return

    try:
        await client.files.delete(file_id)
    except Exception as exc:  # pragma: no cover - 删除失败仅记日志
        logger.warning("删除 DashScope 远端文件失败: file_id=%s err=%s", file_id, exc)


async def extract_fields_from_pdf(
    *,
    file_bytes: bytes,
    filename: str,
    api_key: str,
    base_url: str,
    model: str = DEFAULT_QWEN_DOC_MODEL,
) -> dict[str, Any]:
    """上传 PDF 到 DashScope 并调用 qwen-doc-turbo 抽取字段。"""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    file_id: str | None = None
    summary_task: asyncio.Task[str] | None = None

    try:
        uploaded = await client.files.create(
            file=(filename, file_bytes, "application/pdf"),
            purpose=cast(Any, "file-extract"),
        )
        file_id = uploaded.id

        summary_task = asyncio.create_task(
            _request_file_completion(
                client,
                model=model,
                file_id=file_id,
                prompt=build_document_summary_prompt(),
            )
        )

        fast_extraction_error: Exception | None = None
        fast_content = ""
        extracted_fields: list[dict[str, Any]] = []

        try:
            fast_content = await _request_file_completion(
                client,
                model=model,
                file_id=file_id,
                prompt=build_default_extraction_prompt(),
            )
            extracted_fields = parse_extracted_fields(fast_content)
            if not extracted_fields:
                raise ValueError("模型未返回任何项目")
        except Exception as exc:  # noqa: BLE001 - 快路径失败时回退旧逻辑
            fast_extraction_error = exc

        if fast_extraction_error is None:
            project_ids = _extract_project_ids_from_payloads(extracted_fields)
            summary_content = await summary_task
            return {
                "filename": filename,
                "model": model,
                "file_id": file_id,
                "parse_mode": DEFAULT_PARSE_MODE,
                "page_count": None,
                "document_summary": summary_content.strip(),
                "project_ids": project_ids,
                "extracted_fields": extracted_fields,
                "raw_response": {
                    "project_list": "",
                    "summary": summary_content,
                    "projects": [
                        {"project_id": "fastpath", "content": fast_content}
                    ],
                },
            }

        logger.info(
            "qwen-doc fast path unusable, falling back to project fan-out: %s",
            fast_extraction_error,
        )
        (
            project_list_content,
            project_ids,
            extracted_fields,
            project_responses,
        ) = await _extract_fields_via_project_fallback(
            client,
            model=model,
            file_id=file_id,
            file_bytes=file_bytes,
        )
        summary_content = await summary_task

        return {
            "filename": filename,
            "model": model,
            "file_id": file_id,
            "parse_mode": DEFAULT_PARSE_MODE,
            "page_count": None,
            "document_summary": summary_content.strip(),
            "project_ids": project_ids,
            "extracted_fields": extracted_fields,
            "raw_response": {
                "project_list": project_list_content,
                "summary": summary_content,
                "projects": project_responses,
            },
        }
    except json.JSONDecodeError as exc:
        raise QwenDocExtractionError(
            "MODEL_INVALID_JSON",
            "模型返回内容不是合法 JSON",
            status_code=422,
            file_id=file_id,
        ) from exc
    except ValueError as exc:
        raise QwenDocExtractionError(
            "MODEL_INVALID_PAYLOAD",
            str(exc),
            status_code=422,
            file_id=file_id,
        ) from exc
    except QwenDocExtractionError:
        raise
    except Exception as exc:
        status_code = 502
        code = "MODEL_REQUEST_FAILED" if file_id else "FILE_UPLOAD_FAILED"
        message = "模型调用失败" if file_id else "文件上传失败"
        raise QwenDocExtractionError(
            code,
            message,
            status_code=status_code,
            file_id=file_id,
        ) from exc
    finally:
        if summary_task and not summary_task.done():
            summary_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await summary_task
        await _safe_delete_remote_file(client, file_id)
