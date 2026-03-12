import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "openclaw/skills/pdf-analysis/scripts/ragforge_pdf.py"
SPEC = importlib.util.spec_from_file_location("ragforge_pdf", MODULE_PATH)
ragforge_pdf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ragforge_pdf)


class MergeMarkdownChunkerConfigTests(unittest.TestCase):
    def test_merge_markdown_chunker_preserves_existing_sections(self):
        existing = {
            "query": {"top_k": 8},
            "embedding": {"provider": "siliconflow", "model": "Qwen/Qwen3-Embedding-8B"},
            "ingestion": {"generate_summary": True},
        }

        merged = ragforge_pdf.merge_markdown_chunker_config(existing, chunk_size=1024, chunk_overlap=200)

        self.assertEqual(merged["query"], {"top_k": 8})
        self.assertEqual(
            merged["embedding"],
            {"provider": "siliconflow", "model": "Qwen/Qwen3-Embedding-8B"},
        )
        self.assertTrue(merged["ingestion"]["generate_summary"])
        self.assertEqual(
            merged["ingestion"]["chunker"],
            {"name": "markdown", "params": {"chunk_size": 1024, "chunk_overlap": 200}},
        )


class ResolveApiKeyTests(unittest.TestCase):
    def test_prefers_skill_key_then_repo_key_then_repo_admin_key(self):
        self.assertEqual(
            ragforge_pdf.resolve_api_key_value(
                {"RAGFORGE_API_KEY": "skill-key"},
                {"RAGFORGE_API_KEY": "repo-key", "RAGFORGE_ADMIN_KEY": "repo-admin"},
            ),
            "skill-key",
        )
        self.assertEqual(
            ragforge_pdf.resolve_api_key_value(
                {"RAGFORGE_API_KEY": ""},
                {"RAGFORGE_API_KEY": "repo-key", "RAGFORGE_ADMIN_KEY": "repo-admin"},
            ),
            "repo-key",
        )
        self.assertEqual(
            ragforge_pdf.resolve_api_key_value(
                {"RAGFORGE_API_KEY": ""},
                {"RAGFORGE_ADMIN_KEY": "repo-admin"},
            ),
            "repo-admin",
        )


class DocumentProcessingTests(unittest.TestCase):
    def test_only_terminal_status_stops_polling(self):
        self.assertFalse(ragforge_pdf.document_processing_complete({"processing_status": "pending"}))
        self.assertFalse(ragforge_pdf.document_processing_complete({"processing_status": "processing"}))
        self.assertTrue(ragforge_pdf.document_processing_complete({"processing_status": "completed"}))
        self.assertTrue(ragforge_pdf.document_processing_complete({"processing_status": "failed"}))

    def test_indexed_chunks_mark_ingestion_ready(self):
        chunks = {
            "items": [
                {"indexing_status": "indexed"},
                {"indexing_status": "indexed"},
                {"indexing_status": "pending"},
            ]
        }
        summary = ragforge_pdf.summarize_chunk_indexing(chunks)
        self.assertEqual(summary["indexed_chunk_count"], 2)
        self.assertEqual(summary["total_chunk_count"], 3)
        self.assertTrue(summary["ingestion_ready"])


class CustomFieldsPromptTests(unittest.TestCase):
    def test_build_custom_fields_query_includes_all_fields_and_json_requirement(self):
        query = ragforge_pdf.build_custom_fields_query(["产品定位", "核心卖点", "商业模式"])

        self.assertIn("产品定位", query)
        self.assertIn("核心卖点", query)
        self.assertIn("商业模式", query)
        self.assertIn("JSON", query)
        self.assertIn("缺失", query)

    def test_parse_custom_field_answer_json(self):
        parsed = ragforge_pdf.parse_custom_field_answer(
            '{"fields":{"产品定位":"AI公众号智能采集分析系统"},"missing_fields":["商业模式"]}'
        )
        self.assertEqual(parsed["fields"]["产品定位"], "AI公众号智能采集分析系统")
        self.assertEqual(parsed["missing_fields"], ["商业模式"])


class DeliveryAttachmentPathTests(unittest.TestCase):
    def test_prepare_delivery_attachment_copies_file_to_openclaw_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = pathlib.Path(tmpdir) / "state"
            source_dir = pathlib.Path(tmpdir) / "exports"
            source_dir.mkdir(parents=True, exist_ok=True)
            source = source_dir / "result.xlsx"
            source.write_bytes(b"excel")

            with mock.patch.dict(os.environ, {"OPENCLAW_STATE_DIR": str(state_dir)}, clear=False):
                delivery = ragforge_pdf.prepare_delivery_attachment(source)

            self.assertEqual(delivery, (state_dir / "workspace" / "result.xlsx").resolve())
            self.assertTrue(delivery.exists())
            self.assertEqual(delivery.read_bytes(), b"excel")

    def test_prepare_delivery_attachment_keeps_workspace_file_in_place(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = pathlib.Path(tmpdir) / "state"
            workspace = state_dir / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            source = workspace / "result.xlsx"
            source.write_bytes(b"excel")

            with mock.patch.dict(os.environ, {"OPENCLAW_STATE_DIR": str(state_dir)}, clear=False):
                delivery = ragforge_pdf.prepare_delivery_attachment(source)

            self.assertEqual(delivery, source.resolve())


if __name__ == "__main__":
    unittest.main()
