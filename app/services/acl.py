"""
ACL 权限服务模块

提供文档级访问控制列表（ACL）和敏感度级别检查功能。
用于 Security Trimming，在检索时自动过滤无权限的文档。

敏感度级别（简化为两级）：
- public: 公开，租户内所有 API Key 可访问
- restricted: 受限，需要 ACL 白名单匹配才能访问

注意：为兼容旧数据，internal/confidential/secret 会被视为 restricted 处理

ACL 白名单：
- acl_allow_users: 允许访问的用户 ID 列表
- acl_allow_roles: 允许访问的角色列表
- acl_allow_groups: 允许访问的组/部门列表

身份来源：
- 从 API Key 的 identity 字段获取（见 APIKeyContext.get_user_context()）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# 敏感度级别类型（新版两级）
SensitivityLevel = Literal["public", "restricted"]

# 旧版敏感度级别（向后兼容）
LEGACY_SENSITIVITY_LEVELS = {"internal", "confidential", "secret"}


def normalize_sensitivity(level: str) -> SensitivityLevel:
    """
    标准化敏感度级别
    
    将旧版四级敏感度映射到新版两级：
    - public -> public
    - internal/confidential/secret -> restricted
    """
    if level == "public":
        return "public"
    return "restricted"


@dataclass
class UserContext:
    """
    用户上下文信息，用于 ACL 检查
    
    身份信息来源：API Key 的 identity 字段
    
    Attributes:
        user_id: 用户 ID（用于匹配 acl_allow_users）
        roles: 用户角色列表（用于匹配 acl_allow_roles）
        groups: 用户所属组/部门列表（用于匹配 acl_allow_groups）
        sensitivity_clearance: 敏感度访问级别（public/restricted）
        is_admin: 是否为管理员（API Key role=admin 时为 True）
    """
    user_id: str | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None
    sensitivity_clearance: SensitivityLevel = "public"
    is_admin: bool = False
    
    def can_access_sensitivity(self, level: str) -> bool:
        """
        检查用户是否可以访问指定敏感度级别
        
        Args:
            level: 文档敏感度级别（可能是旧版值）
        """
        if self.is_admin:
            return True
        
        # 标准化敏感度级别
        normalized = normalize_sensitivity(level)
        user_clearance = normalize_sensitivity(self.sensitivity_clearance)
        
        # public 可以访问 public
        # restricted 可以访问 public 和 restricted
        if normalized == "public":
            return True
        return user_clearance == "restricted"


@dataclass
class DocumentACL:
    """
    文档 ACL 信息
    
    Attributes:
        document_id: 文档 ID
        sensitivity_level: 敏感度级别
        allow_users: 允许访问的用户 ID 列表
        allow_roles: 允许访问的角色列表
        allow_groups: 允许访问的组/部门列表
    """
    document_id: str
    sensitivity_level: SensitivityLevel = "internal"
    allow_users: list[str] | None = None
    allow_roles: list[str] | None = None
    allow_groups: list[str] | None = None


def check_document_access(user: UserContext, doc_acl: DocumentACL) -> bool:
    """
    检查用户是否可以访问文档
    
    访问规则（简化为两级）：
    1. 管理员（is_admin=True）可以访问所有文档
    2. public 文档：所有人可访问
    3. restricted 文档：需要 ACL 白名单匹配 + 敏感度级别够
    
    Args:
        user: 用户上下文（来自 API Key 的 identity 字段）
        doc_acl: 文档 ACL 信息
    
    Returns:
        True 如果用户可以访问，False 否则
    """
    # 管理员可以访问所有文档
    if user.is_admin:
        return True
    
    # 标准化敏感度级别
    normalized_level = normalize_sensitivity(doc_acl.sensitivity_level)
    
    # public 文档：所有人可访问
    if normalized_level == "public":
        return True
    
    # restricted 文档：需要检查用户敏感度级别 + ACL 白名单
    # 首先检查用户是否有 restricted 访问权限
    if not user.can_access_sensitivity(doc_acl.sensitivity_level):
        return False
    
    # 检查 ACL 白名单
    has_acl = (
        doc_acl.allow_users or 
        doc_acl.allow_roles or 
        doc_acl.allow_groups
    )
    
    if not has_acl:
        # 没有 ACL 白名单的 restricted 文档，只有管理员可以访问
        return False
    
    # 检查用户 ID
    if doc_acl.allow_users and user.user_id:
        if user.user_id in doc_acl.allow_users:
            return True
    
    # 检查角色
    if doc_acl.allow_roles and user.roles:
        if set(user.roles) & set(doc_acl.allow_roles):
            return True
    
    # 检查组/部门
    if doc_acl.allow_groups and user.groups:
        if set(user.groups) & set(doc_acl.allow_groups):
            return True
    
    return False


def build_acl_filter_for_qdrant(user: UserContext) -> dict | None:
    """
    构建 Qdrant 向量库的 ACL 过滤条件
    
    根据用户上下文生成 Qdrant Filter 条件，用于 Security Trimming。
    返回的条件应添加到搜索时的 must 条件中。
    
    简化后的规则：
    - 管理员：不需要过滤
    - 普通用户：可以访问 public 文档 + ACL 白名单匹配的 restricted 文档
    
    Args:
        user: 用户上下文（来自 API Key 的 identity 字段）
    
    Returns:
        Qdrant Filter 条件字典，或 None（管理员不需要过滤）
    """
    # 管理员不需要 ACL 过滤
    if user.is_admin:
        return None
    
    # 条件1：public 文档（所有人可访问）
    # 注意：要兼容旧数据，public 只匹配 "public"
    public_condition = {
        "key": "sensitivity_level",
        "match": {"value": "public"}
    }
    
    # 条件2：用户在 ACL 白名单中（可以访问 restricted 文档）
    acl_conditions = []
    
    if user.user_id:
        acl_conditions.append({
            "key": "acl_users",
            "match": {"any": [user.user_id]}
        })
    
    if user.roles:
        acl_conditions.append({
            "key": "acl_roles",
            "match": {"any": user.roles}
        })
    
    if user.groups:
        acl_conditions.append({
            "key": "acl_groups",
            "match": {"any": user.groups}
        })
    
    # 构建最终的 OR 条件
    # (sensitivity_level == "public") OR (user in ACL whitelist)
    filter_config = {
        "should": [
            public_condition,
            *acl_conditions
        ]
    }
    
    return filter_config


def build_acl_metadata_for_chunk(
    document_id: str,
    sensitivity_level: str = "public",
    allow_users: list[str] | None = None,
    allow_roles: list[str] | None = None,
    allow_groups: list[str] | None = None,
) -> dict:
    """
    构建 Chunk 的 ACL 元数据，用于存储到向量库
    
    在文档摄取时调用，将 ACL 信息嵌入到每个 chunk 的 payload 中。
    
    Args:
        document_id: 文档 ID
        sensitivity_level: 敏感度级别
        allow_users: 允许访问的用户 ID 列表
        allow_roles: 允许访问的角色列表
        allow_groups: 允许访问的组/部门列表
    
    Returns:
        ACL 元数据字典
    """
    acl_metadata = {
        "sensitivity_level": sensitivity_level,
    }
    
    if allow_users:
        acl_metadata["acl_users"] = allow_users
    
    if allow_roles:
        acl_metadata["acl_roles"] = allow_roles
    
    if allow_groups:
        acl_metadata["acl_groups"] = allow_groups
    
    return acl_metadata


def filter_results_by_acl(
    results: list[dict],
    user: UserContext,
) -> list[dict]:
    """
    后处理：根据 ACL 过滤检索结果
    
    作为向量库 ACL 过滤的补充，进行二次安全修整。
    主要用于处理向量库不支持的复杂 ACL 逻辑。
    
    Args:
        results: 检索结果列表，每个结果包含 metadata 字段
        user: 用户上下文
    
    Returns:
        过滤后的结果列表
    """
    if user.is_admin:
        return results
    
    filtered = []
    for result in results:
        metadata = result.get("metadata", {})
        
        doc_acl = DocumentACL(
            document_id=metadata.get("document_id", ""),
            sensitivity_level=metadata.get("sensitivity_level", "internal"),
            allow_users=metadata.get("acl_users"),
            allow_roles=metadata.get("acl_roles"),
            allow_groups=metadata.get("acl_groups"),
        )
        
        if check_document_access(user, doc_acl):
            filtered.append(result)
        else:
            logger.debug(
                f"ACL 过滤: 用户 {user.user_id} 无权访问文档 {doc_acl.document_id}"
            )
    
    return filtered
