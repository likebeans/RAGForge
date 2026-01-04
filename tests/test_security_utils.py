import pytest

from app.auth.api_key import MemoryRateLimiter
from app.services.acl import UserContext, build_acl_filter_for_qdrant
from app.infra.vector_store import get_acl_filter_ctx, set_acl_filter_ctx, reset_acl_filter_ctx


@pytest.mark.asyncio
async def test_memory_rate_limiter_allows_within_limit():
    limiter = MemoryRateLimiter(window_seconds=60, max_requests=2)
    assert await limiter.allow("k1")
    assert await limiter.allow("k1")
    # 第三个请求应被拒绝
    assert await limiter.allow("k1") is False
    # 新 key 不受影响
    assert await limiter.allow("k2")


def test_acl_filter_for_non_admin():
    user = UserContext(
        user_id="u1",
        roles=["r1"],
        groups=["g1"],
        sensitivity_clearance="restricted",
        is_admin=False,
    )
    flt = build_acl_filter_for_qdrant(user)
    assert flt is not None
    should = flt.get("should", [])
    keys = {c["key"] for c in should}
    assert {"sensitivity_level", "acl_roles", "acl_groups", "acl_users"} & keys


def test_acl_filter_for_admin_is_none():
    user = UserContext(is_admin=True)
    assert build_acl_filter_for_qdrant(user) is None


def test_acl_filter_context_var_roundtrip():
    token = set_acl_filter_ctx({"should": [{"key": "foo", "match": {"value": "bar"}}]})
    try:
        ctx = get_acl_filter_ctx()
        assert ctx is not None
        assert ctx["should"][0]["key"] == "foo"
    finally:
        reset_acl_filter_ctx(token)
        assert get_acl_filter_ctx() is None
