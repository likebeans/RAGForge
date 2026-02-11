"""
Self-RAG Pipeline 演示界面

使用方法:
    pip install streamlit requests
    streamlit run demo_ui.py
"""

import requests
import streamlit as st

# 页面配置
st.set_page_config(
    page_title="Self-RAG Pipeline Demo",
    page_icon="🔍",
    layout="wide",
)

# 默认配置
DEFAULT_API_BASE = "http://localhost:8020"

# 初始化 session state
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE
if "selected_kb" not in st.session_state:
    st.session_state.selected_kb = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def api_request(method: str, endpoint: str, data: dict = None, files: dict = None) -> dict:
    """发送 API 请求"""
    url = f"{st.session_state.api_base}{endpoint}"
    headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=60)
        elif method == "POST":
            if files:
                resp = requests.post(url, headers=headers, files=files, timeout=120)
            else:
                headers["Content-Type"] = "application/json"
                resp = requests.post(url, headers=headers, json=data, timeout=120)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"error": f"不支持的方法: {method}"}
        
        if resp.status_code == 204:
            return {"success": True}
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "连接失败，请检查 API 服务是否运行"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except Exception as e:
        return {"error": str(e)}


def check_connection() -> bool:
    """检查 API 连接"""
    try:
        resp = requests.get(f"{st.session_state.api_base}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# 侧边栏 - 配置
with st.sidebar:
    st.title("⚙️ 配置")
    
    # API 配置
    st.session_state.api_base = st.text_input(
        "API 地址",
        value=st.session_state.api_base,
        help="RAG 服务的 API 地址"
    )
    
    st.session_state.api_key = st.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        help="租户的 API Key"
    )
    
    # 连接状态
    if st.button("🔄 测试连接"):
        if check_connection():
            st.success("✅ 连接成功")
        else:
            st.error("❌ 连接失败")
    
    st.divider()
    
    # 知识库选择
    st.subheader("📚 知识库")
    
    if st.session_state.api_key:
        if st.button("刷新知识库列表"):
            st.rerun()
        
        kb_list = api_request("GET", "/v1/knowledge-bases")
        if "items" in kb_list:
            kb_options = {kb["name"]: kb["id"] for kb in kb_list["items"]}
            if kb_options:
                selected_name = st.selectbox(
                    "选择知识库",
                    options=list(kb_options.keys()),
                    key="kb_selector"
                )
                st.session_state.selected_kb = kb_options.get(selected_name)
                st.caption(f"ID: {st.session_state.selected_kb}")
            else:
                st.info("暂无知识库")
        elif "error" in kb_list:
            st.error(kb_list["error"])
    else:
        st.info("请先输入 API Key")

# 主页面
st.title("🔍 Self-RAG Pipeline 演示")

# 创建标签页
tab1, tab2, tab3, tab4 = st.tabs(["💬 RAG 问答", "📁 知识库管理", "📄 文档上传", "🔬 检索器对比"])

# Tab 1: RAG 问答
with tab1:
    st.subheader("RAG 问答")
    
    if not st.session_state.api_key:
        st.warning("请在左侧输入 API Key")
    elif not st.session_state.selected_kb:
        st.warning("请在左侧选择知识库")
    else:
        # 检索器选择
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            retriever = st.selectbox(
                "检索器",
                ["dense", "bm25", "hybrid", "hyde", "fusion", "multi_query"],
                help="选择检索算法"
            )
        with col2:
            top_k = st.slider("Top K", 1, 20, 5)
        with col3:
            use_rerank = st.checkbox("启用 Rerank", value=False)
        
        # 问题输入
        query = st.text_area("输入问题", height=100, placeholder="请输入您的问题...")
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            submit = st.button("🚀 提交", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ 清空历史"):
                st.session_state.chat_history = []
                st.rerun()
        
        if submit and query:
            with st.spinner("正在生成回答..."):
                # 构建请求
                data = {
                    "query": query,
                    "knowledge_base_ids": [st.session_state.selected_kb],
                    "top_k": top_k,
                }
                
                # 设置检索器
                if retriever != "dense":
                    if retriever == "fusion" and use_rerank:
                        data["retriever_override"] = {"name": "fusion", "params": {"rerank": True}}
                    else:
                        data["retriever_override"] = {"name": retriever}
                
                # 调用 RAG API
                result = api_request("POST", "/v1/rag", data)
                
                if "error" in result:
                    st.error(f"错误: {result['error']}")
                elif "detail" in result:
                    st.error(f"错误: {result['detail']}")
                else:
                    # 保存到历史
                    st.session_state.chat_history.append({
                        "query": query,
                        "answer": result.get("answer", ""),
                        "retriever": result.get("model", {}).get("retriever", retriever),
                        "sources": result.get("retrieval_count", 0),
                    })
        
        # 显示历史
        if st.session_state.chat_history:
            st.divider()
            for i, item in enumerate(reversed(st.session_state.chat_history)):
                with st.container():
                    st.markdown(f"**🙋 问题:** {item['query']}")
                    st.markdown(f"**🤖 回答:** {item['answer']}")
                    st.caption(f"检索器: {item['retriever']} | 来源数: {item['sources']}")
                    st.divider()

# Tab 2: 知识库管理
with tab2:
    st.subheader("知识库管理")
    
    if not st.session_state.api_key:
        st.warning("请在左侧输入 API Key")
    else:
        # 创建知识库
        with st.expander("➕ 创建新知识库", expanded=False):
            kb_name = st.text_input("知识库名称", key="new_kb_name")
            kb_desc = st.text_input("描述（可选）", key="new_kb_desc")
            
            col1, col2 = st.columns(2)
            with col1:
                chunker = st.selectbox(
                    "切分器",
                    ["sliding_window", "recursive", "markdown", "simple"],
                    key="new_kb_chunker"
                )
            with col2:
                retriever_default = st.selectbox(
                    "默认检索器",
                    ["dense", "hybrid", "bm25", "hyde"],
                    key="new_kb_retriever"
                )
            
            if st.button("创建知识库", key="create_kb_btn"):
                if kb_name:
                    data = {
                        "name": kb_name,
                        "description": kb_desc,
                        "config": {
                            "ingestion": {"chunker": {"name": chunker}},
                            "query": {"retriever": {"name": retriever_default}}
                        }
                    }
                    result = api_request("POST", "/v1/knowledge-bases", data)
                    if "id" in result:
                        st.success(f"创建成功！ID: {result['id']}")
                        st.rerun()
                    else:
                        st.error(f"创建失败: {result}")
                else:
                    st.warning("请输入知识库名称")
        
        # 知识库列表
        st.divider()
        kb_list = api_request("GET", "/v1/knowledge-bases")
        
        if "items" in kb_list:
            st.write(f"共 {kb_list.get('total', 0)} 个知识库")
            
            for kb in kb_list["items"]:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{kb['name']}**")
                        st.caption(f"ID: {kb['id']}")
                        if kb.get("description"):
                            st.caption(kb["description"])
                    with col2:
                        # 获取文档数
                        docs = api_request("GET", f"/v1/knowledge-bases/{kb['id']}/documents")
                        doc_count = docs.get("total", 0) if "total" in docs else "?"
                        st.metric("文档数", doc_count)
                    with col3:
                        if st.button("🗑️", key=f"del_{kb['id']}", help="删除知识库"):
                            result = api_request("DELETE", f"/v1/knowledge-bases/{kb['id']}")
                            if result.get("success") or "error" not in result:
                                st.success("已删除")
                                st.rerun()
                            else:
                                st.error(f"删除失败: {result}")
                    st.divider()
        elif "error" in kb_list:
            st.error(kb_list["error"])

# Tab 3: 文档上传
with tab3:
    st.subheader("文档上传")
    
    if not st.session_state.api_key:
        st.warning("请在左侧输入 API Key")
    elif not st.session_state.selected_kb:
        st.warning("请在左侧选择知识库")
    else:
        st.info(f"当前知识库: {st.session_state.selected_kb}")
        
        upload_method = st.radio("上传方式", ["文件上传", "文本输入", "URL 拉取"], horizontal=True)
        
        if upload_method == "文件上传":
            uploaded_files = st.file_uploader(
                "选择文件",
                type=["md", "txt", "pdf"],
                accept_multiple_files=True
            )
            
            if uploaded_files and st.button("上传文件", type="primary"):
                progress = st.progress(0)
                for i, file in enumerate(uploaded_files):
                    with st.spinner(f"上传 {file.name}..."):
                        files = {"file": (file.name, file.getvalue())}
                        result = api_request(
                            "POST",
                            f"/v1/knowledge-bases/{st.session_state.selected_kb}/documents/upload",
                            files=files
                        )
                        if "chunk_count" in result:
                            st.success(f"✅ {file.name}: {result['chunk_count']} chunks")
                        else:
                            st.error(f"❌ {file.name}: {result}")
                    progress.progress((i + 1) / len(uploaded_files))
        
        elif upload_method == "文本输入":
            doc_title = st.text_input("文档标题")
            doc_content = st.text_area("文档内容", height=300)
            
            if st.button("提交文档", type="primary"):
                if doc_title and doc_content:
                    data = {"title": doc_title, "content": doc_content}
                    result = api_request(
                        "POST",
                        f"/v1/knowledge-bases/{st.session_state.selected_kb}/documents",
                        data
                    )
                    if "chunk_count" in result:
                        st.success(f"上传成功！生成 {result['chunk_count']} 个 chunks")
                    else:
                        st.error(f"上传失败: {result}")
                else:
                    st.warning("请输入标题和内容")
        
        else:  # URL 拉取
            doc_url = st.text_input("文档 URL", placeholder="https://example.com/doc.md")
            doc_title_url = st.text_input("文档标题（可选）")
            
            if st.button("拉取文档", type="primary"):
                if doc_url:
                    data = {"source_url": doc_url}
                    if doc_title_url:
                        data["title"] = doc_title_url
                    result = api_request(
                        "POST",
                        f"/v1/knowledge-bases/{st.session_state.selected_kb}/documents",
                        data
                    )
                    if "chunk_count" in result:
                        st.success(f"拉取成功！生成 {result['chunk_count']} 个 chunks")
                    else:
                        st.error(f"拉取失败: {result}")
                else:
                    st.warning("请输入 URL")
        
        # 显示当前文档列表
        st.divider()
        st.subheader("📋 当前文档")
        
        docs = api_request("GET", f"/v1/knowledge-bases/{st.session_state.selected_kb}/documents")
        if "items" in docs:
            if docs["items"]:
                for doc in docs["items"]:
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.write(f"📄 {doc['title']}")
                    with col2:
                        st.caption(f"{doc.get('chunk_count', '?')} chunks")
                    with col3:
                        if st.button("🗑️", key=f"del_doc_{doc['id']}"):
                            api_request("DELETE", f"/v1/documents/{doc['id']}")
                            st.rerun()
            else:
                st.info("暂无文档")
        elif "error" in docs:
            st.error(docs["error"])

# Tab 4: 检索器对比
with tab4:
    st.subheader("检索器对比")
    
    if not st.session_state.api_key:
        st.warning("请在左侧输入 API Key")
    elif not st.session_state.selected_kb:
        st.warning("请在左侧选择知识库")
    else:
        compare_query = st.text_input("输入查询", key="compare_query")
        
        col1, col2 = st.columns(2)
        with col1:
            retrievers_to_compare = st.multiselect(
                "选择要对比的检索器",
                ["dense", "bm25", "hybrid", "hyde", "fusion"],
                default=["dense", "hybrid"]
            )
        with col2:
            compare_top_k = st.slider("Top K", 1, 10, 3, key="compare_top_k")
        
        if st.button("🔍 开始对比", type="primary") and compare_query:
            results = {}
            
            progress = st.progress(0)
            for i, ret in enumerate(retrievers_to_compare):
                with st.spinner(f"正在使用 {ret} 检索..."):
                    data = {
                        "query": compare_query,
                        "knowledge_base_ids": [st.session_state.selected_kb],
                        "top_k": compare_top_k,
                    }
                    if ret != "dense":
                        data["retriever_override"] = {"name": ret}
                    
                    result = api_request("POST", "/v1/retrieve", data)
                    results[ret] = result
                progress.progress((i + 1) / len(retrievers_to_compare))
            
            # 显示对比结果
            cols = st.columns(len(retrievers_to_compare))
            for i, (ret, result) in enumerate(results.items()):
                with cols[i]:
                    st.markdown(f"### {ret}")
                    if "results" in result:
                        for j, r in enumerate(result["results"]):
                            score = r.get("score", 0)
                            text = r.get("text", "")[:200] + "..." if len(r.get("text", "")) > 200 else r.get("text", "")
                            st.markdown(f"**#{j+1}** (score: {score:.4f})")
                            st.caption(text)
                            st.divider()
                    elif "error" in result:
                        st.error(result["error"])
                    elif "detail" in result:
                        st.error(str(result["detail"]))

# 页脚
st.divider()
st.caption("Self-RAG Pipeline Demo | 使用 Streamlit 构建")
