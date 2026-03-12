#!/usr/bin/env python3
"""Direct RagForge PDF analysis CLI for the OpenClaw pdf-analysis skill."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Iterable
from urllib import error, request


DEFAULT_KB_ID = "71dd8415-8a4b-4543-b6f0-8f11e3b88176"
DEFAULT_SCHEMA_ID = "fa1baff3-553d-415f-b9c0-1afd4f90eb93"
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_CHUNK_OVERLAP = 200


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_api_key_value(skill_config: dict[str, str], repo_env: dict[str, str]) -> str:
    return (
        skill_config.get("RAGFORGE_API_KEY", "").strip()
        or repo_env.get("RAGFORGE_API_KEY", "").strip()
        or repo_env.get("RAGFORGE_ADMIN_KEY", "").strip()
    )


def load_config() -> dict[str, str]:
    """Load key-value config from config.env with environment overrides."""
    config_path = Path(__file__).resolve().parent.parent / "config.env"
    repo_env_path = Path(__file__).resolve().parents[4] / ".env"
    config = parse_env_file(config_path)
    repo_env = parse_env_file(repo_env_path)

    env_defaults = {
        "RAGFORGE_BASE_URL": config.get("RAGFORGE_BASE_URL", "http://localhost:8020"),
        "RAGFORGE_API_KEY": resolve_api_key_value(config, repo_env),
        "DEFAULT_KB_ID": config.get("DEFAULT_KB_ID", DEFAULT_KB_ID),
        "DEFAULT_SCHEMA_ID": config.get("DEFAULT_SCHEMA_ID", DEFAULT_SCHEMA_ID),
        "DEFAULT_CHUNK_SIZE": config.get("DEFAULT_CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)),
        "DEFAULT_CHUNK_OVERLAP": config.get("DEFAULT_CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP)),
    }

    for key, default in env_defaults.items():
        config[key] = os.environ.get(key, default)

    return config


def require_api_key(config: dict[str, str]) -> str:
    api_key = config.get("RAGFORGE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("错误：请在 config.env 或环境变量中设置 RAGFORGE_API_KEY")
    return api_key


def http_request(
    method: str,
    url: str,
    token: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    parse: str = "json",
):
    req = request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    for key, value in (headers or {}).items():
        req.add_header(key, value)

    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} 失败: {exc.code} {exc.reason} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {url} 失败: {exc.reason}") from exc

    if parse == "bytes":
        return payload
    if parse == "json":
        if not payload:
            return {}
        return json.loads(payload.decode("utf-8"))
    return payload.decode("utf-8")


def build_multipart_body(
    text_fields: Iterable[tuple[str, str]],
    file_fields: Iterable[tuple[str, str, bytes, str]],
) -> tuple[bytes, str]:
    boundary = f"----OpenClawBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    for field_name, value in text_fields:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode())
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")

    for field_name, filename, content, mime_type in file_fields:
        parts.append(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        parts.append(disposition.encode())
        parts.append(f"Content-Type: {mime_type}\r\n\r\n".encode())
        parts.append(content)
        parts.append(b"\r\n")

    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def api_get_json(base_url: str, token: str, path: str) -> dict:
    return http_request("GET", f"{base_url}{path}", token, parse="json")


def api_patch_json(base_url: str, token: str, path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    return http_request(
        "PATCH",
        f"{base_url}{path}",
        token,
        body=body,
        headers={"Content-Type": "application/json"},
        parse="json",
    )


def api_post_json(base_url: str, token: str, path: str, payload: dict, timeout: int = 120) -> dict:
    body = json.dumps(payload).encode("utf-8")
    return http_request(
        "POST",
        f"{base_url}{path}",
        token,
        body=body,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
        parse="json",
    )


def api_post_multipart(
    base_url: str,
    token: str,
    path: str,
    text_fields: Iterable[tuple[str, str]],
    file_fields: Iterable[tuple[str, str, bytes, str]],
    timeout: int = 600,
    parse: str = "json",
):
    body, boundary = build_multipart_body(text_fields, file_fields)
    return http_request(
        "POST",
        f"{base_url}{path}",
        token,
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=timeout,
        parse=parse,
    )


def resolve_pdf_paths(pdf_args: list[str]) -> list[Path]:
    if not pdf_args:
        raise SystemExit("错误：至少指定一个 --pdf 文件")

    resolved: list[Path] = []
    for raw_path in pdf_args:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"错误：文件不存在: {raw_path}")
        if path.suffix.lower() != ".pdf":
            raise SystemExit(f"错误：不是 PDF 文件: {raw_path}")
        resolved.append(path)
    return resolved


def merge_markdown_chunker_config(existing: dict | None, chunk_size: int, chunk_overlap: int) -> dict:
    merged = copy.deepcopy(existing or {})
    ingestion = copy.deepcopy(merged.get("ingestion") or {})
    ingestion["chunker"] = {
        "name": "markdown",
        "params": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
    }
    merged["ingestion"] = ingestion
    return merged


def sync_markdown_chunker(base_url: str, token: str, kb_id: str, chunk_size: int, chunk_overlap: int) -> dict:
    kb = api_get_json(base_url, token, f"/v1/knowledge-bases/{kb_id}")
    current_config = kb.get("config") or {}
    merged_config = merge_markdown_chunker_config(current_config, chunk_size, chunk_overlap)

    if merged_config == current_config:
        return {
            "updated": False,
            "knowledge_base_id": kb_id,
            "knowledge_base_name": kb.get("name"),
            "config": current_config,
        }

    updated_kb = api_patch_json(
        base_url,
        token,
        f"/v1/knowledge-bases/{kb_id}",
        {"config": merged_config},
    )
    return {
        "updated": True,
        "knowledge_base_id": kb_id,
        "knowledge_base_name": updated_kb.get("name", kb.get("name")),
        "config": updated_kb.get("config", merged_config),
    }


def upload_pdf_to_knowledge_base(base_url: str, token: str, kb_id: str, pdf_path: Path) -> dict:
    file_bytes = pdf_path.read_bytes()
    return api_post_multipart(
        base_url,
        token,
        f"/v1/knowledge-bases/{kb_id}/documents/upload",
        text_fields=[("title", pdf_path.stem), ("source", "pdf")],
        file_fields=[("file", pdf_path.name, file_bytes, "application/pdf")],
        timeout=600,
        parse="json",
    )


def get_document(base_url: str, token: str, document_id: str) -> dict:
    return api_get_json(base_url, token, f"/v1/documents/{document_id}")


def get_document_chunks(base_url: str, token: str, document_id: str) -> dict:
    return api_get_json(base_url, token, f"/v1/documents/{document_id}/chunks")


def document_processing_complete(document: dict) -> bool:
    return (document.get("processing_status") or "").lower() in {"completed", "failed"}


def summarize_chunk_indexing(chunks_payload: dict) -> dict[str, int | bool]:
    items = chunks_payload.get("items") or []
    indexed = sum(1 for item in items if (item.get("indexing_status") or "").lower() == "indexed")
    total = len(items)
    return {
        "indexed_chunk_count": indexed,
        "total_chunk_count": total,
        "ingestion_ready": indexed > 0,
    }


def wait_for_document_details(base_url: str, token: str, document_id: str, attempts: int = 15, delay_seconds: float = 1.0) -> dict:
    last_seen: dict = {}
    for _ in range(attempts):
        details = get_document(base_url, token, document_id)
        last_seen = details
        if document_processing_complete(details):
            return details
        time.sleep(delay_seconds)
    return last_seen


def extract_from_pdfs(base_url: str, token: str, schema_id: str, pdf_paths: list[Path], output_format: str):
    file_fields = [
        ("files", pdf_path.name, pdf_path.read_bytes(), "application/pdf")
        for pdf_path in pdf_paths
    ]
    return api_post_multipart(
        base_url,
        token,
        f"/v1/extraction-schemas/{schema_id}/extract",
        text_fields=[("output_format", output_format)],
        file_fields=file_fields,
        timeout=600,
        parse="bytes" if output_format == "excel" else "json",
    )


def default_output_path(pdf_paths: list[Path], output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    if len(pdf_paths) == 1:
        return pdf_paths[0].with_name(f"{pdf_paths[0].stem}_提取结果.xlsx")
    return Path.cwd() / "ragforge_extraction_result.xlsx"


def resolve_openclaw_state_dir() -> Path:
    return Path(os.environ.get("OPENCLAW_STATE_DIR", "~/.openclaw")).expanduser().resolve()


def resolve_openclaw_workspace_dir() -> Path:
    return resolve_openclaw_state_dir() / "workspace"


def prepare_delivery_attachment(output_path: Path) -> Path:
    resolved_output = output_path.expanduser().resolve()
    workspace_dir = resolve_openclaw_workspace_dir()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    try:
        resolved_output.relative_to(workspace_dir)
        return resolved_output
    except ValueError:
        delivery_path = workspace_dir / resolved_output.name
        shutil.copy2(resolved_output, delivery_path)
        return delivery_path.resolve()


def normalize_extraction_items(extraction_json) -> list[dict]:
    if isinstance(extraction_json, list):
        return [item for item in extraction_json if isinstance(item, dict)]
    if isinstance(extraction_json, dict):
        for key in ("items", "results", "data"):
            value = extraction_json.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def preview_extraction(extraction_json) -> list[dict]:
    items = normalize_extraction_items(extraction_json)
    return items[:3]


def build_custom_fields_query(fields: list[str]) -> str:
    quoted_fields = "、".join(fields)
    return (
        "请仅基于已检索到的文档内容，提取以下字段并返回严格 JSON。"
        f"字段包括：{quoted_fields}。"
        "如果文档中没有明确提到某个字段，请把该字段值设为 null，并在缺失字段 missing_fields 数组中列出字段名。"
        "输出格式必须是 JSON，对象包含两部分：fields 和 missing_fields。"
    )


def parse_custom_field_answer(answer: str):
    try:
        return json.loads(answer)
    except (TypeError, json.JSONDecodeError):
        return answer


def run_custom_fields_query(base_url: str, token: str, kb_id: str, fields: list[str], top_k: int = 5) -> dict:
    query = build_custom_fields_query(fields)
    payload = {
        "query": query,
        "knowledge_base_ids": [kb_id],
        "top_k": top_k,
        "include_sources": True,
        "temperature": 0,
    }
    try:
        result = api_post_json(base_url, token, "/v1/rag", payload, timeout=180)
        result["mode"] = "rag"
        return result
    except RuntimeError as exc:
        retrieve_result = api_post_json(
            base_url,
            token,
            "/v1/retrieve",
            {
                "query": query,
                "knowledge_base_ids": [kb_id],
                "top_k": top_k,
            },
            timeout=120,
        )
        return {
            "mode": "retrieve_fallback",
            "error": str(exc),
            "query": query,
            "results": retrieve_result.get("results", []),
        }


def cmd_schemas(config: dict[str, str]) -> None:
    base_url = config["RAGFORGE_BASE_URL"].rstrip("/")
    token = require_api_key(config)
    result = api_get_json(base_url, token, "/v1/extraction-schemas")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_knowledge_bases(config: dict[str, str]) -> None:
    base_url = config["RAGFORGE_BASE_URL"].rstrip("/")
    token = require_api_key(config)
    result = api_get_json(base_url, token, "/v1/knowledge-bases")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_run(config: dict[str, str], args: argparse.Namespace) -> None:
    base_url = config["RAGFORGE_BASE_URL"].rstrip("/")
    token = require_api_key(config)
    pdf_paths = resolve_pdf_paths(args.pdf)
    kb_id = args.kb_id or config["DEFAULT_KB_ID"]
    schema_id = args.schema_id or config["DEFAULT_SCHEMA_ID"]
    chunk_size = args.chunk_size or int(config["DEFAULT_CHUNK_SIZE"])
    chunk_overlap = args.chunk_overlap or int(config["DEFAULT_CHUNK_OVERLAP"])

    result: dict[str, object] = {
        "files": [str(path) for path in pdf_paths],
        "knowledge_base_id": kb_id,
        "schema_id": schema_id,
        "steps_completed": [],
    }

    if not args.skip_kb_sync:
        kb_sync = sync_markdown_chunker(base_url, token, kb_id, chunk_size, chunk_overlap)
        result["knowledge_base_sync"] = kb_sync
        result["steps_completed"].append("sync_markdown_chunker")

    if not args.skip_ingest:
        uploads = []
        for pdf_path in pdf_paths:
            upload_result = upload_pdf_to_knowledge_base(base_url, token, kb_id, pdf_path)
            document_id = upload_result.get("document_id")
            if document_id:
                details = wait_for_document_details(base_url, token, document_id)
                chunk_summary = summarize_chunk_indexing(get_document_chunks(base_url, token, document_id))
                upload_result = {
                    **upload_result,
                    "chunk_count": details.get("chunk_count", upload_result.get("chunk_count", 0)),
                    "processing_status": details.get("processing_status"),
                    "parser": (details.get("metadata") or {}).get("parser"),
                    **chunk_summary,
                }
            uploads.append(upload_result)
        result["knowledge_base_uploads"] = uploads
        result["steps_completed"].append("ingest_to_knowledge_base")

    if not args.skip_extract:
        extraction_json = extract_from_pdfs(base_url, token, schema_id, pdf_paths, output_format="json")
        excel_bytes = extract_from_pdfs(base_url, token, schema_id, pdf_paths, output_format="excel")
        output_path = default_output_path(pdf_paths, args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(excel_bytes)
        delivery_path = prepare_delivery_attachment(output_path)

        result["extraction_preview"] = preview_extraction(extraction_json)
        result["excel_output"] = str(output_path)
        result["delivery_media_path"] = str(delivery_path)
        result["steps_completed"].append("extract_json")
        result["steps_completed"].append("export_excel")
        result["steps_completed"].append("prepare_delivery_attachment")

    if args.field:
        custom_field_result = run_custom_fields_query(base_url, token, kb_id, args.field, top_k=args.top_k)
        result["custom_fields_requested"] = args.field
        if isinstance(custom_field_result, dict) and "answer" in custom_field_result:
            custom_field_result["parsed_answer"] = parse_custom_field_answer(custom_field_result["answer"])
        result["custom_field_result"] = custom_field_result
        result["steps_completed"].append("extract_custom_fields")

    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct RagForge PDF analysis CLI")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("schemas", help="列出提取模板")
    subparsers.add_parser("knowledge-bases", help="列出知识库")

    run_parser = subparsers.add_parser("run", help="执行 PDF 提取 + 导出 + 入库")
    run_parser.add_argument("--pdf", action="append", required=True, help="PDF 文件路径（可多次指定）")
    run_parser.add_argument("--schema-id", help="提取模板 ID，默认使用产品信息提取模板")
    run_parser.add_argument("--kb-id", help="知识库 ID，默认使用项目管理知识库")
    run_parser.add_argument("--output", help="Excel 导出路径")
    run_parser.add_argument("--chunk-size", type=int, help="Markdown chunk size")
    run_parser.add_argument("--chunk-overlap", type=int, help="Markdown chunk overlap")
    run_parser.add_argument("--field", action="append", help="按用户需求提取的字段，可多次指定")
    run_parser.add_argument("--top-k", type=int, default=5, help="自定义字段提取时的检索条数")
    run_parser.add_argument("--skip-kb-sync", action="store_true", help="跳过知识库 Markdown chunker 配置同步")
    run_parser.add_argument("--skip-ingest", action="store_true", help="跳过知识库入库")
    run_parser.add_argument("--skip-extract", action="store_true", help="跳过结构化提取与 Excel 导出")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()

    if not args.command:
        parser.print_help()
        raise SystemExit(1)

    try:
        if args.command == "schemas":
            cmd_schemas(config)
        elif args.command == "knowledge-bases":
            cmd_knowledge_bases(config)
        elif args.command == "run":
            cmd_run(config, args)
    except Exception as exc:  # pragma: no cover - surfaced to CLI caller
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
