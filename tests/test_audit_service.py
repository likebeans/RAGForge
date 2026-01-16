"""
审计日志服务单元测试

测试 app/services/audit.py 的功能：
- 数据脱敏
- 敏感字段处理
"""

import pytest
from app.services.audit import _sanitize_data, SENSITIVE_FIELDS


class TestSanitizeData:
    """测试数据脱敏函数"""
    
    def test_sanitize_none(self):
        """测试 None 输入"""
        result = _sanitize_data(None)
        assert result is None
    
    def test_sanitize_empty_dict(self):
        """测试空字典"""
        result = _sanitize_data({})
        # 空字典被视为 falsy，返回 None
        assert result is None or result == "{}"
    
    def test_sanitize_normal_data(self):
        """测试普通数据不变"""
        data = {"name": "test", "count": 10}
        result = _sanitize_data(data)
        assert "name" in result
        assert "count" in result
    
    def test_sanitize_password_field(self):
        """测试密码字段脱敏"""
        data = {"username": "admin", "password": "secret123"}
        result = _sanitize_data(data)
        assert "***" in result
        assert "secret123" not in result
    
    def test_sanitize_api_key_field(self):
        """测试 API Key 字段脱敏"""
        data = {"api_key": "sk_test_12345", "other": "value"}
        result = _sanitize_data(data)
        assert "***" in result
        assert "sk_test_12345" not in result
    
    def test_sanitize_token_field(self):
        """测试 Token 字段脱敏"""
        data = {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "data": "test"}
        result = _sanitize_data(data)
        assert "***" in result
    
    def test_sanitize_secret_field(self):
        """测试 Secret 字段脱敏"""
        data = {"secret": "my_secret_value", "public": "public_value"}
        result = _sanitize_data(data)
        assert "***" in result
        assert "my_secret_value" not in result
    
    def test_sanitize_authorization_field(self):
        """测试 Authorization 字段脱敏"""
        data = {"authorization": "Bearer token123", "method": "GET"}
        result = _sanitize_data(data)
        assert "***" in result
        assert "Bearer token123" not in result
    
    def test_sanitize_case_insensitive(self):
        """测试大小写不敏感"""
        data = {"PASSWORD": "secret", "Api_Key": "key123"}
        result = _sanitize_data(data)
        # 应该都被脱敏
        assert "secret" not in result
        assert "key123" not in result
    
    def test_sanitize_long_string(self):
        """测试长字符串截断"""
        long_value = "x" * 1000
        data = {"content": long_value}
        result = _sanitize_data(data, max_length=500)
        # 应该被截断
        assert len(result) <= 510  # 加上 "..." 和其他字符
    
    def test_sanitize_list_value(self):
        """测试列表值处理"""
        data = {"items": [1, 2, 3, 4, 5]}
        result = _sanitize_data(data)
        assert "list" in result.lower() or "len=5" in result
    
    def test_sanitize_dict_value(self):
        """测试字典值处理"""
        data = {"nested": {"a": 1, "b": 2}}
        result = _sanitize_data(data)
        assert "dict" in result.lower() or "len=2" in result
    
    def test_sanitize_max_length(self):
        """测试最大长度限制"""
        data = {f"key_{i}": f"value_{i}" for i in range(100)}
        result = _sanitize_data(data, max_length=200)
        # 结果应该被截断
        assert len(result) <= 210  # max_length + "..."


class TestSensitiveFields:
    """测试敏感字段配置"""
    
    def test_sensitive_fields_defined(self):
        """测试敏感字段已定义"""
        assert "password" in SENSITIVE_FIELDS
        assert "api_key" in SENSITIVE_FIELDS
        assert "token" in SENSITIVE_FIELDS
        assert "secret" in SENSITIVE_FIELDS
        assert "authorization" in SENSITIVE_FIELDS
    
    def test_sensitive_fields_is_set(self):
        """测试敏感字段是集合类型"""
        assert isinstance(SENSITIVE_FIELDS, set)
