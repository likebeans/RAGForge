from app.middleware.audit import _get_action_from_path


def test_audit_action_mappings():
    assert _get_action_from_path("POST", "/v1/retrieve") == "retrieve"
    assert _get_action_from_path("POST", "/v1/rag") == "rag"
    assert _get_action_from_path("POST", "/v1/chat/completions") == "rag_chat"
    assert _get_action_from_path("POST", "/v1/embeddings") == "embedding"
    assert _get_action_from_path("POST", "/admin/tenants") == "admin_tenant_create"
    assert _get_action_from_path("DELETE", "/v1/knowledge-bases/1") == "kb_delete"
    assert _get_action_from_path("PATCH", "/v1/knowledge-bases/1") == "kb_update"
    assert _get_action_from_path("GET", "/v1/api-keys") == "apikey_read"
    assert _get_action_from_path("DELETE", "/v1/api-keys/1") == "apikey_delete"
    assert _get_action_from_path("GET", "/unknown") is None
