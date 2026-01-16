"""
配置校验服务单元测试

测试 app/services/config_validation.py 的功能：
- validate_kb_config
- 切分器校验
- 检索器校验
- Embedding 配置校验
"""

import pytest
from app.services.config_validation import (
    validate_kb_config,
    ConfigValidationError,
    VALID_EMBEDDING_PROVIDERS,
)


class TestValidateKbConfig:
    """测试 validate_kb_config 函数"""
    
    def test_valid_empty_config(self):
        """测试空配置（使用默认值）"""
        # 空配置应该使用默认值，不抛出异常
        validate_kb_config({})
    
    def test_valid_simple_config(self):
        """测试简单有效配置"""
        config = {
            "ingestion": {
                "chunker": {
                    "name": "simple",
                    "params": {"max_chars": 1000}
                }
            },
            "query": {
                "retriever": {
                    "name": "dense"
                }
            }
        }
        validate_kb_config(config)
    
    def test_valid_complex_config(self):
        """测试复杂有效配置"""
        config = {
            "ingestion": {
                "chunker": {
                    "name": "recursive",
                    "params": {"chunk_size": 1024, "chunk_overlap": 200}
                },
                "store": {
                    "type": "qdrant"
                }
            },
            "query": {
                "retriever": {
                    "name": "hybrid",
                    "params": {"dense_weight": 0.7}
                }
            }
        }
        validate_kb_config(config)
    
    def test_invalid_config_type(self):
        """测试无效配置类型"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config("not a dict")
        assert "必须是对象" in str(exc_info.value)
    
    def test_unknown_chunker(self):
        """测试未知切分器"""
        config = {
            "ingestion": {
                "chunker": {
                    "name": "unknown_chunker"
                }
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "未知 chunker" in str(exc_info.value)
    
    def test_unknown_retriever(self):
        """测试未知检索器"""
        config = {
            "query": {
                "retriever": {
                    "name": "unknown_retriever"
                }
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "未知 retriever" in str(exc_info.value)
    
    def test_valid_chunker_names(self):
        """测试所有有效切分器名称"""
        valid_chunkers = ["simple", "sliding_window", "recursive", "markdown", "code", "parent_child"]
        for chunker_name in valid_chunkers:
            config = {
                "ingestion": {
                    "chunker": {"name": chunker_name}
                }
            }
            validate_kb_config(config)
    
    def test_valid_retriever_names(self):
        """测试所有有效检索器名称"""
        valid_retrievers = ["dense", "hybrid", "fusion", "hyde", "multi_query"]
        for retriever_name in valid_retrievers:
            config = {
                "query": {
                    "retriever": {"name": retriever_name}
                }
            }
            validate_kb_config(config)
    
    def test_valid_store_types(self):
        """测试有效的存储类型"""
        for store_type in ["qdrant", "milvus", "es"]:
            config = {
                "ingestion": {
                    "store": {"type": store_type}
                }
            }
            validate_kb_config(config)
    
    def test_invalid_store_type(self):
        """测试无效的存储类型"""
        config = {
            "ingestion": {
                "store": {"type": "unknown_store"}
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "未知向量存储类型" in str(exc_info.value)
    
    def test_skip_qdrant_boolean(self):
        """测试 skip_qdrant 必须是布尔值"""
        config = {
            "ingestion": {
                "store": {"skip_qdrant": "not a boolean"}
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "skip_qdrant 必须为布尔值" in str(exc_info.value)


class TestEmbeddingConfigValidation:
    """测试 Embedding 配置校验"""
    
    def test_valid_embedding_providers(self):
        """测试有效的 embedding 提供商"""
        for provider in VALID_EMBEDDING_PROVIDERS:
            config = {
                "embedding": {
                    "provider": provider,
                    "model": "test-model"
                }
            }
            validate_kb_config(config)
    
    def test_invalid_embedding_provider(self):
        """测试无效的 embedding 提供商"""
        config = {
            "embedding": {
                "provider": "unknown_provider",
                "model": "test-model"
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "未知 embedding 提供商" in str(exc_info.value)
    
    def test_embedding_provider_requires_model(self):
        """测试指定 provider 时必须指定 model"""
        config = {
            "embedding": {
                "provider": "openai"
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "必须同时指定 embedding.model" in str(exc_info.value)
    
    def test_embedding_dim_must_be_positive(self):
        """测试 dim 必须是正整数"""
        config = {
            "embedding": {
                "dim": -100
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "embedding.dim 必须是正整数" in str(exc_info.value)
    
    def test_embedding_dim_max_value(self):
        """测试 dim 不能超过 8192"""
        config = {
            "embedding": {
                "dim": 10000
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config)
        assert "不能超过 8192" in str(exc_info.value)
    
    def test_embedding_change_with_documents(self):
        """测试有文档时不能更改 embedding 配置"""
        config = {
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small"
            }
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_kb_config(config, has_documents=True)
        assert "知识库已有文档" in str(exc_info.value)
    
    def test_embedding_config_without_documents(self):
        """测试无文档时可以设置 embedding 配置"""
        config = {
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "dim": 1536
            }
        }
        validate_kb_config(config, has_documents=False)


class TestConfigValidationError:
    """测试 ConfigValidationError 异常"""
    
    def test_error_is_value_error(self):
        """测试 ConfigValidationError 是 ValueError 的子类"""
        assert issubclass(ConfigValidationError, ValueError)
    
    def test_error_message(self):
        """测试错误消息"""
        error = ConfigValidationError("测试错误消息")
        assert str(error) == "测试错误消息"
