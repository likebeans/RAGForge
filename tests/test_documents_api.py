from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routes import documents


@pytest.mark.asyncio
async def test_get_document_returns_processing_status():
    tenant = SimpleNamespace(id="tenant-1")
    db = AsyncMock()
    doc = SimpleNamespace(
        id="doc-1",
        title="Demo",
        knowledge_base_id="kb-1",
        extra_metadata={"source": "pdf"},
        source="pdf",
        created_at=datetime(2026, 3, 16, tzinfo=timezone.utc),
        summary="Summary",
        summary_status="completed",
        processing_log="[INFO] done",
        processing_status="completed",
    )
    kb = SimpleNamespace(id="kb-1", tenant_id="tenant-1")
    result_proxy = SimpleNamespace(first=lambda: (doc, kb, 3))
    db.execute.return_value = result_proxy

    result = await documents.get_document(
        doc_id="doc-1",
        tenant=tenant,
        _=None,
        db=db,
    )

    assert result.processing_status == "completed"
    assert result.chunk_count == 3
