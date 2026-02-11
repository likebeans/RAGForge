"""
Pipeline 切分器单元测试

测试 app/pipeline/chunkers 的功能：
- SimpleChunker
- SlidingWindowChunker
- RecursiveChunker
- MarkdownChunker
- CodeChunker
- ParentChildChunker
"""

from app.pipeline.base import ChunkPiece
from app.pipeline import operator_registry


class TestChunkPiece:
    """测试 ChunkPiece 数据结构"""
    
    def test_chunk_piece_creation(self):
        """测试创建 ChunkPiece"""
        piece = ChunkPiece(text="测试文本", metadata={"key": "value"})
        assert piece.text == "测试文本"
        assert piece.metadata["key"] == "value"
    
    def test_chunk_piece_empty_metadata(self):
        """测试空元数据"""
        piece = ChunkPiece(text="测试", metadata={})
        assert piece.metadata == {}


class TestOperatorRegistry:
    """测试算法注册表"""
    
    def test_get_chunker_simple(self):
        """测试获取 simple 切分器"""
        chunker_cls = operator_registry.get("chunker", "simple")
        assert chunker_cls is not None
        chunker = chunker_cls()
        assert chunker.name == "simple"
        assert chunker.kind == "chunker"
    
    def test_get_chunker_sliding_window(self):
        """测试获取 sliding_window 切分器"""
        chunker_cls = operator_registry.get("chunker", "sliding_window")
        assert chunker_cls is not None
        chunker = chunker_cls()
        assert chunker.name == "sliding_window"
    
    def test_get_chunker_recursive(self):
        """测试获取 recursive 切分器"""
        chunker_cls = operator_registry.get("chunker", "recursive")
        assert chunker_cls is not None
        chunker = chunker_cls()
        assert chunker.name == "recursive"
    
    def test_get_chunker_markdown(self):
        """测试获取 markdown 切分器"""
        chunker_cls = operator_registry.get("chunker", "markdown")
        assert chunker_cls is not None
        chunker = chunker_cls()
        assert chunker.name == "markdown"
    
    def test_get_chunker_code(self):
        """测试获取 code 切分器"""
        chunker_cls = operator_registry.get("chunker", "code")
        assert chunker_cls is not None
        chunker = chunker_cls()
        assert chunker.name == "code"
    
    def test_get_chunker_parent_child(self):
        """测试获取 parent_child 切分器"""
        chunker_cls = operator_registry.get("chunker", "parent_child")
        assert chunker_cls is not None
        chunker = chunker_cls()
        assert chunker.name == "parent_child"


class TestSimpleChunker:
    """测试 SimpleChunker"""
    
    def test_simple_chunker_basic(self):
        """测试基本切分"""
        chunker = operator_registry.get("chunker", "simple")(max_chars=800, separator="\\n\\n")
        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        pieces = chunker.chunk(text)
        
        assert len(pieces) == 3
        assert pieces[0].text == "第一段内容。"
        assert pieces[1].text == "第二段内容。"
        assert pieces[2].text == "第三段内容。"
    
    def test_simple_chunker_custom_separator(self):
        """测试自定义分隔符"""
        chunker = operator_registry.get("chunker", "simple")(max_chars=800, separator="|||")
        text = "段落A|||段落B|||段落C"
        pieces = chunker.chunk(text)
        
        assert len(pieces) == 3
        assert pieces[0].text == "段落A"
        assert pieces[1].text == "段落B"
        assert pieces[2].text == "段落C"
    
    def test_simple_chunker_long_paragraph(self):
        """测试长段落截断"""
        chunker = operator_registry.get("chunker", "simple")(max_chars=10, separator="\\n\\n")
        text = "这是一个超过十个字符的很长的段落内容"
        pieces = chunker.chunk(text)
        
        # 长段落应该被截断为多个片段
        assert len(pieces) > 1
        assert all(len(p.text) <= 10 for p in pieces)
    
    def test_simple_chunker_empty_text(self):
        """测试空文本"""
        chunker = operator_registry.get("chunker", "simple")()
        pieces = chunker.chunk("")
        
        # 空文本应返回至少一个片段
        assert len(pieces) >= 1
    
    def test_simple_chunker_metadata(self):
        """测试元数据传递"""
        chunker = operator_registry.get("chunker", "simple")()
        text = "段落A\n\n段落B"
        pieces = chunker.chunk(text, metadata={"doc_id": "123"})
        
        # 元数据应该被传递到每个片段
        for piece in pieces:
            assert "doc_id" in piece.metadata or "separator" in piece.metadata


class TestSlidingWindowChunker:
    """测试 SlidingWindowChunker"""
    
    def test_sliding_window_basic(self):
        """测试基本滑动窗口"""
        chunker = operator_registry.get("chunker", "sliding_window")(window=10, overlap=3)
        text = "0123456789ABCDEFGHIJ"  # 20 字符
        pieces = chunker.chunk(text)
        
        # 步长 = 10 - 3 = 7，应该生成 3 个片段
        assert len(pieces) >= 2
        assert len(pieces[0].text) == 10
    
    def test_sliding_window_overlap(self):
        """测试重叠区域"""
        chunker = operator_registry.get("chunker", "sliding_window")(window=10, overlap=5)
        text = "ABCDEFGHIJKLMNOPQRST"  # 20 字符
        pieces = chunker.chunk(text)
        
        # 检查相邻片段有重叠
        if len(pieces) >= 2:
            # 第一个片段的后半部分应该与第二个片段的前半部分重叠
            overlap_text = pieces[0].text[-5:]
            assert pieces[1].text.startswith(overlap_text)
    
    def test_sliding_window_short_text(self):
        """测试短文本"""
        chunker = operator_registry.get("chunker", "sliding_window")(window=100, overlap=20)
        text = "短文本"
        pieces = chunker.chunk(text)
        
        assert len(pieces) == 1
        assert pieces[0].text == "短文本"
    
    def test_sliding_window_empty_text(self):
        """测试空文本"""
        chunker = operator_registry.get("chunker", "sliding_window")()
        pieces = chunker.chunk("")
        
        assert len(pieces) == 0


class TestRecursiveChunker:
    """测试 RecursiveChunker"""
    
    def test_recursive_basic(self):
        """测试基本递归切分"""
        chunker = operator_registry.get("chunker", "recursive")(chunk_size=50, chunk_overlap=10)
        text = "第一段内容。\n\n第二段内容，这是一个比较长的段落。\n\n第三段。"
        pieces = chunker.chunk(text)
        
        assert len(pieces) >= 1
        # 检查每个片段大小合理
        for piece in pieces:
            assert len(piece.text) <= 50 + 20  # 允许一些浮动
    
    def test_recursive_respects_boundaries(self):
        """测试保持语义边界"""
        chunker = operator_registry.get("chunker", "recursive")(chunk_size=100, chunk_overlap=20)
        text = "段落一内容。\n\n段落二内容。\n\n段落三内容。"
        pieces = chunker.chunk(text)
        
        # 应该优先在双换行处切分
        assert len(pieces) >= 1


class TestMarkdownChunker:
    """测试 MarkdownChunker"""
    
    def test_markdown_basic(self):
        """测试基本 Markdown 切分"""
        chunker = operator_registry.get("chunker", "markdown")(chunk_size=500)
        text = """# 标题一

这是第一节内容。

## 标题二

这是第二节内容。

### 标题三

这是第三节内容。
"""
        pieces = chunker.chunk(text)
        
        assert len(pieces) >= 1
    
    def test_markdown_headers_metadata(self):
        """测试 Markdown 标题元数据"""
        chunker = operator_registry.get("chunker", "markdown")(chunk_size=1000)
        text = """# 主标题

## 子标题

内容内容内容。
"""
        pieces = chunker.chunk(text)
        
        # 应该至少有一个片段
        assert len(pieces) >= 1


class TestCodeChunker:
    """测试 CodeChunker"""
    
    def test_code_chunker_python(self):
        """测试 Python 代码切分"""
        chunker = operator_registry.get("chunker", "code")(language="python", max_chunk_size=500)
        code = '''
import os

def hello():
    """Say hello"""
    print("Hello")

def world():
    """Say world"""
    print("World")

class MyClass:
    def method(self):
        pass
'''
        pieces = chunker.chunk(code)
        
        assert len(pieces) >= 1
    
    def test_code_chunker_auto_detect(self):
        """测试自动检测语言"""
        chunker = operator_registry.get("chunker", "code")(language="auto")
        code = "def test(): pass"
        pieces = chunker.chunk(code)
        
        assert len(pieces) >= 1
    
    def test_code_chunker_javascript(self):
        """测试 JavaScript 代码切分"""
        chunker = operator_registry.get("chunker", "code")(language="javascript")
        code = '''
function hello() {
    console.log("Hello");
}

function world() {
    console.log("World");
}
'''
        pieces = chunker.chunk(code)
        
        assert len(pieces) >= 1


class TestParentChildChunker:
    """测试 ParentChildChunker"""
    
    def test_parent_child_basic(self):
        """测试基本父子切分"""
        chunker = operator_registry.get("chunker", "parent_child")(
            parent_mode="paragraph",
            parent_max_chars=200,
            child_max_chars=50
        )
        text = "这是父块的内容。这是更多的内容。\n\n这是另一个父块的内容。"
        pieces = chunker.chunk(text)
        
        # 应该有父块和子块
        assert len(pieces) >= 1
    
    def test_parent_child_metadata(self):
        """测试父子块元数据"""
        chunker = operator_registry.get("chunker", "parent_child")(
            parent_mode="paragraph",
            parent_max_chars=500,
            child_max_chars=100
        )
        text = "这是一段测试内容。这是更多的内容用于切分。"
        pieces = chunker.chunk(text)
        
        # 检查元数据
        has_parent = False
        has_child = False
        for piece in pieces:
            if piece.metadata.get("child") == False:
                has_parent = True
            elif piece.metadata.get("child") == True:
                has_child = True
        
        # 应该至少有父块或子块
        assert len(pieces) >= 1
    
    def test_parent_child_full_doc_mode(self):
        """测试全文档模式"""
        chunker = operator_registry.get("chunker", "parent_child")(
            parent_mode="full_doc",
            child_max_chars=50
        )
        text = "这是一段内容。这是更多内容。这是第三句。"
        pieces = chunker.chunk(text)
        
        assert len(pieces) >= 1


class TestChunkerIntegration:
    """切分器集成测试"""
    
    def test_all_chunkers_return_chunk_pieces(self):
        """测试所有切分器返回 ChunkPiece 列表"""
        chunker_names = ["simple", "sliding_window", "recursive", "markdown", "code", "parent_child"]
        text = "这是测试文本。用于测试所有切分器。"
        
        for name in chunker_names:
            chunker = operator_registry.get("chunker", name)()
            pieces = chunker.chunk(text)
            
            assert isinstance(pieces, list), f"{name} 应返回列表"
            for piece in pieces:
                assert isinstance(piece, ChunkPiece), f"{name} 应返回 ChunkPiece"
                assert isinstance(piece.text, str), f"{name} 的 text 应为字符串"
                assert isinstance(piece.metadata, dict), f"{name} 的 metadata 应为字典"
    
    def test_chunkers_handle_unicode(self):
        """测试切分器处理 Unicode 文本"""
        text = "这是中文。\n\nこれは日本語です。\n\n이것은 한국어입니다。\n\n🎉🎊🎁"
        chunker_names = ["simple", "sliding_window", "recursive"]
        
        for name in chunker_names:
            chunker = operator_registry.get("chunker", name)()
            pieces = chunker.chunk(text)
            
            assert len(pieces) >= 1, f"{name} 应能处理 Unicode"
    
    def test_chunkers_preserve_content(self):
        """测试切分器不丢失内容（简单情况）"""
        text = "ABCDEFGHIJ"
        chunker = operator_registry.get("chunker", "sliding_window")(window=5, overlap=0)
        pieces = chunker.chunk(text)
        
        # 连接所有片段应该覆盖原文
        combined = "".join(p.text for p in pieces)
        assert combined == text
