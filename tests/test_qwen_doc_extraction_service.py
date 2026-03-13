import json
import types

import pytest

from app.services.qwen_doc_extraction import (
    QwenDocExtractionError,
    build_default_extraction_prompt,
    build_document_summary_prompt,
    build_project_list_prompt,
    build_project_prompt,
    extract_project_ids_from_text,
    extract_fields_from_pdf,
    parse_extracted_fields,
    parse_project_ids,
)


def test_build_default_extraction_prompt_mentions_array_output():
    prompt = build_default_extraction_prompt()

    assert "JSON数组" in prompt
    assert "未提及" in prompt
    assert "项目" in prompt


def test_build_project_list_prompt_mentions_all_projects():
    prompt = build_project_list_prompt()

    assert "所有项目" in prompt
    assert "JSON数组" in prompt
    assert "ND-003" in prompt


def test_build_project_prompt_mentions_specific_project():
    prompt = build_project_prompt("ND-004")

    assert "ND-004" in prompt
    assert "只提取该项目" in prompt
    assert "JSON对象" in prompt


def test_build_document_summary_prompt_mentions_full_pdf():
    prompt = build_document_summary_prompt()

    assert "整个PDF" in prompt
    assert "简要介绍" in prompt


def test_parse_project_ids_accepts_mixed_payload():
    result = parse_project_ids(
        """```json
        ["ND-003", {"项目": "ND-004"}, {"id": "ND-005"}, "ND-003"]
        ```"""
    )

    assert result == ["ND-003", "ND-004", "ND-005"]


def test_parse_project_ids_filters_single_letter_noise():
    result = parse_project_ids(
        """```json
        ["ND-003", "C-001", "XY001", {"项目": "AB-12"}]
        ```"""
    )

    assert result == ["ND-003", "XY-001"]


def test_extract_project_ids_from_text_keeps_true_project_ids():
    text = """
    ND003 肿瘤、特发性肺纤维化等4个适应症中美双报
    ND-004 HPK1 实体瘤
    ND-017 IL23R 自免性疾病
    C-001 不是项目编号
    """

    result = extract_project_ids_from_text(text)

    assert result == ["ND-003", "ND-004", "ND-017"]


def test_parse_extracted_fields_accepts_fenced_json_array():
    result = parse_extracted_fields(
        """```json
        [{"项目": "ND-003", "靶点": "GLP-1R"}]
        ```"""
    )

    assert result == [{"项目": "ND-003", "靶点": "GLP-1R"}]


@pytest.mark.asyncio
async def test_extract_fields_from_pdf_prefers_single_pass_fast_path(monkeypatch):
    class FakeFilesAPI:
        def __init__(self):
            self.deleted_file_id = None

        async def create(self, file, purpose):
            assert purpose == "file-extract"
            assert file == ("sample.pdf", b"%PDF-1.4", "application/pdf")
            return types.SimpleNamespace(id="file-123")

        async def delete(self, file_id):
            self.deleted_file_id = file_id
            return types.SimpleNamespace(id=file_id, deleted=True)

    class FakeChatCompletionsAPI:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            prompt = kwargs["messages"][-1]["content"]
            if prompt == build_default_extraction_prompt():
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(
                                content=json.dumps(
                                    [
                                        {"项目": "ND-003", "靶点": "GLP-1R"},
                                        {"项目": "ND004", "靶点": "GCGR"},
                                    ],
                                    ensure_ascii=False,
                                )
                            )
                        )
                    ]
                )
            if prompt == build_document_summary_prompt():
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(
                                content="这是一份介绍新药研发平台、融资进展和多条项目管线的商业计划书。"
                            )
                        )
                    ]
                )
            raise AssertionError(f"unexpected prompt: {prompt}")

    fake_files = FakeFilesAPI()
    fake_chat = FakeChatCompletionsAPI()
    fake_client = types.SimpleNamespace(
        files=fake_files,
        chat=types.SimpleNamespace(completions=fake_chat),
    )

    monkeypatch.setattr(
        "app.services.qwen_doc_extraction.AsyncOpenAI",
        lambda **_: fake_client,
    )

    result = await extract_fields_from_pdf(
        file_bytes=b"%PDF-1.4",
        filename="sample.pdf",
        api_key="test-key",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    assert result["filename"] == "sample.pdf"
    assert result["model"] == "qwen-doc-turbo"
    assert result["file_id"] == "file-123"
    assert result["parse_mode"] == "file_id"
    assert result["page_count"] is None
    assert result["document_summary"] == "这是一份介绍新药研发平台、融资进展和多条项目管线的商业计划书。"
    assert result["project_ids"] == ["ND-003", "ND-004"]
    assert result["extracted_fields"] == [
        {"项目": "ND-003", "靶点": "GLP-1R"},
        {"项目": "ND-004", "靶点": "GCGR"},
    ]
    assert result["raw_response"]["project_list"] == ""
    assert len(result["raw_response"]["summary"]) > 0
    assert result["raw_response"]["projects"] == [
        {
            "project_id": "fastpath",
            "content": json.dumps(
                [
                    {"项目": "ND-003", "靶点": "GLP-1R"},
                    {"项目": "ND004", "靶点": "GCGR"},
                ],
                ensure_ascii=False,
            ),
        }
    ]
    assert fake_files.deleted_file_id == "file-123"
    assert len(fake_chat.calls) == 2
    prompts = {call["messages"][-1]["content"] for call in fake_chat.calls}
    assert build_default_extraction_prompt() in prompts
    assert build_document_summary_prompt() in prompts
    assert build_project_list_prompt() not in prompts
    assert all("ND-003" not in prompt and "ND-004" not in prompt for prompt in prompts)


@pytest.mark.asyncio
async def test_extract_fields_from_pdf_falls_back_to_project_fanout_when_fast_path_invalid(
    monkeypatch,
):
    class FakeFilesAPI:
        def __init__(self):
            self.deleted_file_id = None

        async def create(self, file, purpose):
            assert purpose == "file-extract"
            return types.SimpleNamespace(id="file-123")

        async def delete(self, file_id):
            self.deleted_file_id = file_id
            return types.SimpleNamespace(id=file_id, deleted=True)

    class FakeChatCompletionsAPI:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            prompt = kwargs["messages"][-1]["content"]
            if prompt == build_default_extraction_prompt():
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(content="not-json")
                        )
                    ]
                )
            if prompt == build_document_summary_prompt():
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(content="摘要内容")
                        )
                    ]
                )
            if prompt == build_project_list_prompt():
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(
                                content='["ND-003", "ND-004"]'
                            )
                        )
                    ]
                )
            if "ND-003" in prompt:
                content = json.dumps({"项目": "ND003", "靶点": "GLP-1R"}, ensure_ascii=False)
            elif "ND-004" in prompt:
                content = json.dumps({"项目": "ND_004", "靶点": "GCGR"}, ensure_ascii=False)
            else:
                raise AssertionError(f"unexpected prompt: {prompt}")

            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content=content)
                    )
                ]
            )

    fake_files = FakeFilesAPI()
    fake_chat = FakeChatCompletionsAPI()
    fake_client = types.SimpleNamespace(
        files=fake_files,
        chat=types.SimpleNamespace(completions=fake_chat),
    )

    monkeypatch.setattr(
        "app.services.qwen_doc_extraction.AsyncOpenAI",
        lambda **_: fake_client,
    )
    monkeypatch.setattr(
        "app.services.qwen_doc_extraction.extract_project_ids_from_pdf_bytes",
        lambda _: ["ND-003", "ND-004"],
    )

    result = await extract_fields_from_pdf(
        file_bytes=b"%PDF-1.4",
        filename="sample.pdf",
        api_key="test-key",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    assert result["document_summary"] == "摘要内容"
    assert result["project_ids"] == ["ND-003", "ND-004"]
    assert result["extracted_fields"] == [
        {"项目": "ND-003", "靶点": "GLP-1R"},
        {"项目": "ND-004", "靶点": "GCGR"},
    ]
    assert result["raw_response"]["project_list"] == '["ND-003", "ND-004"]'
    assert len(result["raw_response"]["projects"]) == 2
    assert fake_files.deleted_file_id == "file-123"
    assert len(fake_chat.calls) == 5
    prompts = [call["messages"][-1]["content"] for call in fake_chat.calls]
    assert build_default_extraction_prompt() in prompts
    assert build_document_summary_prompt() in prompts
    assert build_project_list_prompt() in prompts
    assert any("ND-003" in prompt for prompt in prompts)
    assert any("ND-004" in prompt for prompt in prompts)


@pytest.mark.asyncio
async def test_extract_fields_from_pdf_raises_on_invalid_json(monkeypatch):
    class FakeFilesAPI:
        def __init__(self):
            self.deleted_file_id = None

        async def create(self, file, purpose):
            return types.SimpleNamespace(id="file-123")

        async def delete(self, file_id):
            self.deleted_file_id = file_id
            return types.SimpleNamespace(id=file_id, deleted=True)

    class FakeChatCompletionsAPI:
        async def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content="not-json")
                    )
                ]
            )

    fake_files = FakeFilesAPI()
    fake_client = types.SimpleNamespace(
        files=fake_files,
        chat=types.SimpleNamespace(completions=FakeChatCompletionsAPI()),
    )

    monkeypatch.setattr(
        "app.services.qwen_doc_extraction.AsyncOpenAI",
        lambda **_: fake_client,
    )

    with pytest.raises(QwenDocExtractionError) as exc_info:
        await extract_fields_from_pdf(
            file_bytes=b"%PDF-1.4",
            filename="sample.pdf",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    assert exc_info.value.code == "MODEL_INVALID_JSON"
    assert exc_info.value.status_code == 422
    assert exc_info.value.file_id == "file-123"
    assert fake_files.deleted_file_id == "file-123"


@pytest.mark.asyncio
async def test_extract_fields_from_pdf_raises_on_upload_failure(monkeypatch):
    class FakeFilesAPI:
        async def create(self, file, purpose):
            raise RuntimeError("upload failed")

        async def delete(self, file_id):
            raise AssertionError("delete should not be called when upload fails")

    fake_client = types.SimpleNamespace(
        files=FakeFilesAPI(),
        chat=types.SimpleNamespace(completions=object()),
    )

    monkeypatch.setattr(
        "app.services.qwen_doc_extraction.AsyncOpenAI",
        lambda **_: fake_client,
    )

    with pytest.raises(QwenDocExtractionError) as exc_info:
        await extract_fields_from_pdf(
            file_bytes=b"%PDF-1.4",
            filename="sample.pdf",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    assert exc_info.value.code == "FILE_UPLOAD_FAILED"
    assert exc_info.value.status_code == 502
    assert exc_info.value.file_id is None
