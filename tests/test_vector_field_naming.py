from app.infra.vector_store import get_vector_field_name


def test_vector_field_name_basic():
    assert get_vector_field_name("bge-m3", 1024) == "vec_bge_m3_1024"
    assert get_vector_field_name("Qwen Embedding 8B", 4096) == "vec_qwen_embedding_8b_4096"
    assert get_vector_field_name(None, 768) == "vec_default_768"
