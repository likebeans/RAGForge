import json
import types
from io import BytesIO

import pytest
from fastapi import UploadFile

from app.api.routes.extraction import extract_with_qwen_plus
from app.services.qwen_doc_extraction import QwenDocExtractionError


class _FakeResolver:
    async def get_llm_config(self, session, tenant=None, request_override=None):
        return {
            "llm_provider": "qwen",
            "llm_model": "qwen-doc-turbo",
        }

    def build_provider_config(self, config, config_type, tenant=None):
        return {
            "provider": "qwen",
            "model": "qwen-doc-turbo",
            "api_key": "test-key",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }


@pytest.mark.asyncio
async def test_extract_with_qwen_plus_rejects_non_pdf():
    file = UploadFile(filename="bad.txt", file=BytesIO(b"hello"))

    response = await extract_with_qwen_plus(
        file=file,
        db=object(),
        tenant=types.SimpleNamespace(id="tenant-1", model_settings={}),
    )

    payload = json.loads(response.body)
    assert response.status_code == 400
    assert payload["error"]["code"] == "INVALID_FILE_TYPE"
    assert payload["error"]["parse_mode"] == "file_id"


@pytest.mark.asyncio
async def test_extract_with_qwen_plus_returns_standardized_payload(monkeypatch):
    async def fake_extract_fields_from_pdf(**kwargs):
        return {
            "filename": kwargs["filename"],
            "model": "qwen-doc-turbo",
            "file_id": "file-123",
            "parse_mode": "file_id",
            "page_count": None,
            "document_summary": "这是一份介绍公司和项目管线的商业计划书。",
            "project_ids": ["ND-003"],
            "extracted_fields": [{"项目": "ND-003"}],
            "raw_response": {"content": '[{"项目": "ND-003"}]'},
        }

    monkeypatch.setattr(
        "app.api.routes.extraction.model_config_resolver",
        _FakeResolver(),
        raising=False,
    )
    monkeypatch.setattr(
        "app.api.routes.extraction.extract_fields_from_pdf",
        fake_extract_fields_from_pdf,
        raising=False,
    )

    file = UploadFile(filename="good.pdf", file=BytesIO(b"%PDF-1.4"))

    response = await extract_with_qwen_plus(
        file=file,
        db=object(),
        tenant=types.SimpleNamespace(id="tenant-1", model_settings={}),
    )

    assert response["model"] == "qwen-doc-turbo"
    assert response["file_id"] == "file-123"
    assert response["parse_mode"] == "file_id"
    assert response["document_summary"] == "这是一份介绍公司和项目管线的商业计划书。"
    assert response["extracted_fields"] == [{"项目": "ND-003"}]


@pytest.mark.asyncio
async def test_extract_with_qwen_plus_maps_service_error(monkeypatch):
    async def fake_extract_fields_from_pdf(**kwargs):
        raise QwenDocExtractionError(
            "MODEL_INVALID_JSON",
            "模型返回内容不是合法 JSON",
            status_code=422,
            file_id="file-123",
        )

    monkeypatch.setattr(
        "app.api.routes.extraction.model_config_resolver",
        _FakeResolver(),
        raising=False,
    )
    monkeypatch.setattr(
        "app.api.routes.extraction.extract_fields_from_pdf",
        fake_extract_fields_from_pdf,
        raising=False,
    )

    file = UploadFile(filename="good.pdf", file=BytesIO(b"%PDF-1.4"))

    response = await extract_with_qwen_plus(
        file=file,
        db=object(),
        tenant=types.SimpleNamespace(id="tenant-1", model_settings={}),
    )

    payload = json.loads(response.body)
    assert response.status_code == 422
    assert payload["error"]["code"] == "MODEL_INVALID_JSON"
    assert payload["error"]["file_id"] == "file-123"
    assert payload["error"]["model"] == "qwen-doc-turbo"
