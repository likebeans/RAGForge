# Qwen Doc PDF Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the image-based implementation behind `POST /v1/extraction-schemas/extract/qwen-plus` with direct PDF upload to DashScope File API plus `qwen-doc-turbo` extraction, while keeping the default 30-field schema and returning a standardized response.

**Architecture:** Introduce a dedicated service module that encapsulates DashScope file upload, `qwen-doc-turbo` invocation, JSON parsing, and best-effort remote file cleanup. Keep the FastAPI route thin: validate the PDF upload, resolve the tenant-aware Qwen provider config, call the service, map service exceptions to HTTP status codes, and return normalized output fields such as `model`, `file_id`, `parse_mode`, and `extracted_fields`.

**Tech Stack:** FastAPI, OpenAI Python SDK (DashScope compatible-mode), pytest, pytest-asyncio

---

### Task 1: Add Qwen Doc extraction service skeleton

**Files:**
- Create: `app/services/qwen_doc_extraction.py`
- Test: `tests/test_qwen_doc_extraction_service.py`

**Step 1: Write the failing test**

```python
from app.services.qwen_doc_extraction import build_default_extraction_prompt


def test_build_default_extraction_prompt_mentions_array_output():
    prompt = build_default_extraction_prompt()
    assert "JSON数组" in prompt
    assert "未提及" in prompt
    assert "项目" in prompt
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py -q`
Expected: FAIL because `app.services.qwen_doc_extraction` does not exist yet.

**Step 3: Write minimal implementation**

```python
from app.pipeline.parsers.pdf_parser import DEFAULT_EXTRACTION_FIELDS


def build_default_extraction_prompt() -> str:
    field_list = "\n".join(f"- {field['name']}" for field in DEFAULT_EXTRACTION_FIELDS)
    return (
        "请提取所有项目并仅返回JSON数组。\n"
        "未提及字段统一填写未提及。\n"
        f"{field_list}"
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_qwen_doc_extraction_service.py app/services/qwen_doc_extraction.py
git commit -m "test: scaffold qwen doc extraction service"
```

### Task 2: Implement upload, model call, JSON normalization, and cleanup

**Files:**
- Modify: `app/services/qwen_doc_extraction.py`
- Test: `tests/test_qwen_doc_extraction_service.py`

**Step 1: Write the failing tests**

```python
import pytest

from app.services.qwen_doc_extraction import (
    QwenDocExtractionError,
    extract_fields_from_pdf,
)


@pytest.mark.asyncio
async def test_extract_fields_from_pdf_returns_standardized_payload(monkeypatch):
    result = await extract_fields_from_pdf(
        file_bytes=b"%PDF-1.4",
        filename="sample.pdf",
        api_key="test-key",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    assert result["model"] == "qwen-doc-turbo"
    assert result["parse_mode"] == "file_id"
    assert isinstance(result["extracted_fields"], list)


@pytest.mark.asyncio
async def test_extract_fields_from_pdf_raises_on_invalid_json(monkeypatch):
    with pytest.raises(QwenDocExtractionError) as exc_info:
        await extract_fields_from_pdf(
            file_bytes=b"%PDF-1.4",
            filename="sample.pdf",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    assert exc_info.value.code == "MODEL_INVALID_JSON"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py -q`
Expected: FAIL because `extract_fields_from_pdf` and `QwenDocExtractionError` are incomplete.

**Step 3: Write minimal implementation**

```python
class QwenDocExtractionError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int, file_id: str | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.file_id = file_id
        super().__init__(message)


async def extract_fields_from_pdf(...):
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    upload = await client.files.create(file=(filename, file_bytes, "application/pdf"), purpose="file-extract")
    file_id = upload.id
    try:
        response = await client.chat.completions.create(
            model="qwen-doc-turbo",
            messages=[...],
            temperature=0.1,
        )
        payload = _parse_json_content(response.choices[0].message.content)
        return {
            "filename": filename,
            "model": "qwen-doc-turbo",
            "file_id": file_id,
            "parse_mode": "file_id",
            "page_count": None,
            "extracted_fields": payload if isinstance(payload, list) else [payload],
            "raw_response": {"content": response.choices[0].message.content},
        }
    finally:
        await _safe_delete_remote_file(client, file_id)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_qwen_doc_extraction_service.py app/services/qwen_doc_extraction.py
git commit -m "feat: add qwen doc pdf extraction service"
```

### Task 3: Replace route internals and standardize HTTP errors

**Files:**
- Modify: `app/api/routes/extraction.py`
- Test: `tests/test_qwen_extraction_route.py`

**Step 1: Write the failing tests**

```python
import io

from fastapi.testclient import TestClient

from app.main import app


def test_qwen_plus_route_rejects_non_pdf(monkeypatch):
    client = TestClient(app)
    response = client.post(
        "/v1/extraction-schemas/extract/qwen-plus",
        files={"file": ("bad.txt", b"hello", "text/plain")},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400


def test_qwen_plus_route_returns_standardized_payload(monkeypatch):
    client = TestClient(app)
    response = client.post(
        "/v1/extraction-schemas/extract/qwen-plus",
        files={"file": ("good.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": "Bearer test-token"},
    )
    data = response.json()
    assert data["model"] == "qwen-doc-turbo"
    assert data["parse_mode"] == "file_id"
    assert "file_id" in data
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_qwen_extraction_route.py -q`
Expected: FAIL because the route still uses image rendering and old response handling.

**Step 3: Write minimal implementation**

```python
@router.post("/extract/qwen-plus")
async def extract_with_qwen_plus(...):
    provider_config = await _resolve_qwen_doc_provider_config(db, tenant)
    filename = file.filename or "unknown.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=_error_payload("INVALID_FILE_TYPE", ...))

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail=_error_payload("EMPTY_FILE", ...))

    try:
        return await extract_fields_from_pdf(...)
    except QwenDocExtractionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_error_payload(exc.code, exc.message, model="qwen-doc-turbo", file_id=exc.file_id),
        ) from exc
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_qwen_extraction_route.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_qwen_extraction_route.py app/api/routes/extraction.py
git commit -m "feat: switch qwen pdf route to qwen-doc-turbo"
```

### Task 4: Add edge-case coverage and regression checks

**Files:**
- Modify: `tests/test_qwen_doc_extraction_service.py`
- Modify: `tests/test_qwen_extraction_route.py`
- Optional reference: `tests/test_extraction_api.py`

**Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_extract_fields_from_pdf_strips_fenced_json(monkeypatch):
    result = await extract_fields_from_pdf(...)
    assert result["extracted_fields"][0]["项目"] == "ND-003"


def test_qwen_plus_route_maps_invalid_json_to_422(monkeypatch):
    response = client.post(...)
    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "MODEL_INVALID_JSON"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py -q`
Expected: FAIL because fenced JSON cleanup and route error mapping are incomplete.

**Step 3: Write minimal implementation**

```python
def _strip_code_fence(content: str) -> str:
    if "```json" in content:
        return content.split("```json", 1)[1].split("```", 1)[0]
    if "```" in content:
        return content.split("```", 1)[1].split("```", 1)[0]
    return content
```

补齐：
- 非法 JSON -> `QwenDocExtractionError(code="MODEL_INVALID_JSON", status_code=422, ...)`
- 上游上传/推理异常 -> `QwenDocExtractionError(..., status_code=502, ...)`
- 删除远端文件失败仅记日志

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py app/services/qwen_doc_extraction.py app/api/routes/extraction.py
git commit -m "test: cover qwen doc extraction edge cases"
```

### Task 5: Final verification

**Files:**
- Verify: `app/services/qwen_doc_extraction.py`
- Verify: `app/api/routes/extraction.py`
- Verify: `tests/test_qwen_doc_extraction_service.py`
- Verify: `tests/test_qwen_extraction_route.py`

**Step 1: Run focused tests**

Run: `uv run pytest tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py -q`
Expected: PASS

**Step 2: Run formatting and lint**

Run: `uv run ruff format app/services/qwen_doc_extraction.py app/api/routes/extraction.py tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py`
Expected: files reformatted or already formatted

Run: `uv run ruff check app/services/qwen_doc_extraction.py app/api/routes/extraction.py tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py`
Expected: PASS

**Step 3: Run type checks for touched production code**

Run: `uv run mypy app/services/qwen_doc_extraction.py app/api/routes/extraction.py`
Expected: PASS

**Step 4: Commit**

```bash
git add app/services/qwen_doc_extraction.py app/api/routes/extraction.py tests/test_qwen_doc_extraction_service.py tests/test_qwen_extraction_route.py docs/plans/2026-03-13-qwen-doc-pdf-extraction-design.md docs/plans/2026-03-13-qwen-doc-pdf-extraction.md
git commit -m "feat: extract pdf fields with qwen doc turbo"
```
