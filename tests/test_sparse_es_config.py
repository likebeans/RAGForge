from app.infra.bm25_es import compute_index_name


def test_compute_index_name_shared():
    name = compute_index_name("kb_", "shared", "t1", "kb1")
    assert name == "kb_shared"


def test_compute_index_name_per_kb():
    name = compute_index_name("kb_", "per_kb", "tenantA", "kbX")
    assert name == "kb_tenanta_kbx"
