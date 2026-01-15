"""
ACL 权限服务单元测试

测试 app/services/acl.py 的功能：
- 权限过滤
- ACL 元数据构建
- 用户上下文处理
"""

import pytest
from app.services.acl import (
    UserContext,
    filter_results_by_acl,
    build_acl_filter_for_qdrant,
    build_acl_metadata_for_chunk,
)


class TestUserContext:
    """测试用户上下文"""
    
    def test_user_context_creation(self):
        """测试创建用户上下文"""
        ctx = UserContext(
            user_id="user_123",
            roles=["admin", "editor"],
            groups=["engineering"],
        )
        
        assert ctx.user_id == "user_123"
        assert "admin" in ctx.roles
        assert "engineering" in ctx.groups


class TestFilterResultsByAcl:
    """测试 ACL 权限过滤"""
    
    def test_filter_no_acl(self):
        """测试无 ACL 限制的文档"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "公开内容",
                "metadata": {"sensitivity_level": "public"},
            },
            {
                "chunk_id": "chunk_2",
                "text": "内部内容",
                "metadata": {},
            },
        ]
        
        ctx = UserContext(user_id="user_123", roles=["viewer"], groups=[])
        
        # 无 ACL 限制的文档应该都能访问
        filtered = filter_results_by_acl(results, ctx)
        assert len(filtered) == 2
    
    def test_filter_by_sensitivity_level(self):
        """测试按敏感度级别过滤"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "公开内容",
                "metadata": {"sensitivity_level": "public"},
            },
            {
                "chunk_id": "chunk_2",
                "text": "机密内容",
                "metadata": {"sensitivity_level": "confidential"},
            },
        ]
        
        # 普通用户只能访问 public 文档
        ctx = UserContext(user_id="user_123", roles=["viewer"], groups=[])
        filtered = filter_results_by_acl(results, ctx)
        assert len(filtered) == 1
        assert filtered[0]["chunk_id"] == "chunk_1"
    
    def test_filter_by_user_id(self):
        """测试按用户 ID 过滤"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "用户 A 的文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_users": ["user_123"],
                },
            },
            {
                "chunk_id": "chunk_2",
                "text": "用户 B 的文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_users": ["user_456"],
                },
            },
        ]
        
        ctx = UserContext(user_id="user_123", roles=[], groups=[])
        filtered = filter_results_by_acl(results, ctx)
        
        # 只能访问自己的文档
        assert len(filtered) == 1
        assert filtered[0]["chunk_id"] == "chunk_1"
    
    def test_filter_by_role(self):
        """测试按角色过滤"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "管理员文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_roles": ["admin"],
                },
            },
            {
                "chunk_id": "chunk_2",
                "text": "编辑者文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_roles": ["editor"],
                },
            },
        ]
        
        ctx = UserContext(user_id="user_123", roles=["admin"], groups=[])
        filtered = filter_results_by_acl(results, ctx)
        
        # 管理员只能访问管理员文档
        assert len(filtered) == 1
        assert filtered[0]["chunk_id"] == "chunk_1"
    
    def test_filter_by_group(self):
        """测试按组过滤"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "工程组文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_groups": ["engineering"],
                },
            },
            {
                "chunk_id": "chunk_2",
                "text": "产品组文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_groups": ["product"],
                },
            },
        ]
        
        ctx = UserContext(user_id="user_123", roles=[], groups=["engineering"])
        filtered = filter_results_by_acl(results, ctx)
        
        # 只能访问工程组文档
        assert len(filtered) == 1
        assert filtered[0]["chunk_id"] == "chunk_1"
    
    def test_filter_multiple_permissions(self):
        """测试多重权限（用户、角色、组）"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "复合权限文档",
                "metadata": {
                    "sensitivity_level": "internal",
                    "acl_allow_users": ["user_456"],
                    "acl_allow_roles": ["admin"],
                    "acl_allow_groups": ["engineering"],
                },
            },
        ]
        
        # 用户不在 allow_users，但在 engineering 组
        ctx = UserContext(user_id="user_123", roles=["viewer"], groups=["engineering"])
        filtered = filter_results_by_acl(results, ctx)
        
        # 应该能访问（满足组权限）
        assert len(filtered) == 1
    
    def test_filter_no_permission(self):
        """测试无权限访问"""
        results = [
            {
                "chunk_id": "chunk_1",
                "text": "受限文档",
                "metadata": {
                    "sensitivity_level": "confidential",
                    "acl_allow_users": ["user_456"],
                    "acl_allow_roles": ["admin"],
                    "acl_allow_groups": ["hr"],
                },
            },
        ]
        
        ctx = UserContext(user_id="user_123", roles=["viewer"], groups=["engineering"])
        filtered = filter_results_by_acl(results, ctx)
        
        # 无权限访问
        assert len(filtered) == 0


class TestBuildAclFilterForQdrant:
    """测试构建 Qdrant ACL 过滤器"""
    
    def test_build_filter_none_context(self):
        """测试无用户上下文"""
        filter_dict = build_acl_filter_for_qdrant(None)
        assert filter_dict is None
    
    def test_build_filter_with_user(self):
        """测试构建用户过滤器"""
        ctx = UserContext(user_id="user_123", roles=["viewer"], groups=["engineering"])
        filter_dict = build_acl_filter_for_qdrant(ctx)
        
        # 应该包含用户、角色、组的过滤条件
        assert filter_dict is not None
        assert "should" in filter_dict or "must" in filter_dict
    
    def test_build_filter_public_access(self):
        """测试公开访问过滤器"""
        ctx = UserContext(user_id="user_123", roles=[], groups=[])
        filter_dict = build_acl_filter_for_qdrant(ctx)
        
        # 应该至少包含 public 敏感度级别的过滤
        assert filter_dict is not None


class TestBuildAclMetadataForChunk:
    """测试构建 Chunk ACL 元数据"""
    
    def test_build_metadata_no_acl(self):
        """测试无 ACL 限制"""
        metadata = build_acl_metadata_for_chunk(
            document_id="doc_123",
            sensitivity_level="internal",
            allow_users=None,
            allow_roles=None,
            allow_groups=None,
        )
        
        assert metadata["document_id"] == "doc_123"
        assert metadata["sensitivity_level"] == "internal"
        assert "acl_allow_users" not in metadata
        assert "acl_allow_roles" not in metadata
        assert "acl_allow_groups" not in metadata
    
    def test_build_metadata_with_users(self):
        """测试包含用户列表"""
        metadata = build_acl_metadata_for_chunk(
            document_id="doc_123",
            sensitivity_level="internal",
            allow_users=["user_123", "user_456"],
            allow_roles=None,
            allow_groups=None,
        )
        
        assert "acl_allow_users" in metadata
        assert isinstance(metadata["acl_allow_users"], list)
        assert "user_123" in metadata["acl_allow_users"]
    
    def test_build_metadata_with_roles(self):
        """测试包含角色列表"""
        metadata = build_acl_metadata_for_chunk(
            document_id="doc_123",
            sensitivity_level="confidential",
            allow_users=None,
            allow_roles=["admin", "editor"],
            allow_groups=None,
        )
        
        assert "acl_allow_roles" in metadata
        assert isinstance(metadata["acl_allow_roles"], list)
        assert "admin" in metadata["acl_allow_roles"]
    
    def test_build_metadata_with_groups(self):
        """测试包含组列表"""
        metadata = build_acl_metadata_for_chunk(
            document_id="doc_123",
            sensitivity_level="internal",
            allow_users=None,
            allow_roles=None,
            allow_groups=["engineering", "product"],
        )
        
        assert "acl_allow_groups" in metadata
        assert isinstance(metadata["acl_allow_groups"], list)
        assert "engineering" in metadata["acl_allow_groups"]
    
    def test_build_metadata_full_acl(self):
        """测试完整 ACL 元数据"""
        metadata = build_acl_metadata_for_chunk(
            document_id="doc_123",
            sensitivity_level="confidential",
            allow_users=["user_123"],
            allow_roles=["admin"],
            allow_groups=["hr"],
        )
        
        assert metadata["document_id"] == "doc_123"
        assert metadata["sensitivity_level"] == "confidential"
        assert "acl_allow_users" in metadata
        assert "acl_allow_roles" in metadata
        assert "acl_allow_groups" in metadata
        assert len(metadata["acl_allow_users"]) == 1
        assert len(metadata["acl_allow_roles"]) == 1
        assert len(metadata["acl_allow_groups"]) == 1
