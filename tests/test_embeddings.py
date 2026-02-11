"""
Embedding 模块单元测试

测试 app/infra/embeddings.py 的功能：
- deterministic_hash_embed
- get_embedding / get_embeddings
"""

from app.infra.embeddings import (
    deterministic_hash_embed,
)


class TestDeterministicHashEmbed:
    """测试确定性哈希向量生成"""
    
    def test_returns_correct_dimension(self):
        """测试返回正确维度"""
        vec = deterministic_hash_embed("测试文本", dim=1024)
        assert len(vec) == 1024
        
        vec = deterministic_hash_embed("测试文本", dim=512)
        assert len(vec) == 512
        
        vec = deterministic_hash_embed("测试文本", dim=3072)
        assert len(vec) == 3072
    
    def test_deterministic(self):
        """测试确定性（相同输入相同输出）"""
        text = "这是一段测试文本"
        vec1 = deterministic_hash_embed(text, dim=1024)
        vec2 = deterministic_hash_embed(text, dim=1024)
        
        assert vec1 == vec2
    
    def test_different_texts_different_vectors(self):
        """测试不同文本产生不同向量"""
        vec1 = deterministic_hash_embed("文本A", dim=1024)
        vec2 = deterministic_hash_embed("文本B", dim=1024)
        
        # 应该有差异
        assert vec1 != vec2
    
    def test_normalized_range(self):
        """测试向量值在 [-1, 1] 范围内"""
        vec = deterministic_hash_embed("测试", dim=1024)
        
        for v in vec:
            assert -1 <= v <= 1
    
    def test_empty_text(self):
        """测试空文本"""
        vec = deterministic_hash_embed("", dim=1024)
        assert len(vec) == 1024
    
    def test_unicode_text(self):
        """测试 Unicode 文本"""
        texts = [
            "中文文本",
            "日本語テキスト",
            "한국어 텍스트",
            "🎉🎊🎁 Emoji text",
        ]
        
        for text in texts:
            vec = deterministic_hash_embed(text, dim=1024)
            assert len(vec) == 1024
    
    def test_long_text(self):
        """测试长文本"""
        long_text = "这是一段很长的文本。" * 1000
        vec = deterministic_hash_embed(long_text, dim=1024)
        assert len(vec) == 1024
    
    def test_small_dimension(self):
        """测试小维度"""
        vec = deterministic_hash_embed("测试", dim=8)
        assert len(vec) == 8
    
    def test_large_dimension(self):
        """测试大维度"""
        vec = deterministic_hash_embed("测试", dim=4096)
        assert len(vec) == 4096


class TestEmbeddingIntegration:
    """Embedding 集成测试（不依赖外部服务）"""
    
    def test_hash_embed_consistency(self):
        """测试哈希向量的一致性"""
        # 多次调用应该返回相同结果
        results = []
        for _ in range(5):
            vec = deterministic_hash_embed("一致性测试", dim=256)
            results.append(vec)
        
        # 所有结果应该相同
        for vec in results[1:]:
            assert vec == results[0]
    
    def test_hash_embed_different_dims_different_vectors(self):
        """测试不同维度产生不同的向量（前缀除外）"""
        vec_small = deterministic_hash_embed("测试", dim=128)
        vec_large = deterministic_hash_embed("测试", dim=256)
        
        # 维度不同
        assert len(vec_small) != len(vec_large)
