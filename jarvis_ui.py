# ==========================================
# jarvis_ui.py
# ==========================================
import streamlit as st
import streamlit.components.v1 as components
import base64

# 預設金鑰放這
DEFAULT_API_KEY = ""

# 純 UI 顯示用的字典放這
MODULES_FOR_UI = {
    "1. 核心流程與底層架構": {
        "Observer Mode": "觀察情緒、立場與衝突，識別最高異常值進行分析。",
        "Meta 鎖定": "鎖定 Meta 語境，防止語場偏離。",
        # ... (其餘內容照舊) ...
    },
    "5. 結尾、反思與收束": {
        "強制收束/反思模組": "輕量短準反思，壓縮條列維持焦點。",
        "反思隱匿化補丁": "反思溶解於句意中，「可被感覺，不可被看見」。"
    }
}

def setup_page():
    """初始化頁面設定"""
    st.set_page_config(page_title="Jarvis Command Center", layout="wide", initial_sidebar_state="expanded")

def render_audio_player(audio_bytes, speed=1.8, autoplay=False):
    """渲染自定義倍速語音播放器 (HTML/JS)"""
    if not audio_bytes: return
    b64 = base64.b64encode(audio_bytes).decode()
    auto_attr = "autoplay" if autoplay else ""
    html_code = f"""
        <audio id="jarvis_audio_{str(hash(audio_bytes))[-5:]}" controls {auto_attr} style="width: 100%; height: 40px;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
            var audio = document.getElementById("jarvis_audio_{str(hash(audio_bytes))[-5:]}");
            audio.playbackRate = {speed};
        </script>
    """
    components.html(html_code, height=50)

def render_sidebar(default_api_key, modules_dict, fetch_models_callback):
    """渲染側邊欄：API 金鑰與模組速查，並回傳使用者的選擇"""
    with st.sidebar:
        st.title("⚙️ Jarvis 系統控制")
        api_key = st.text_input("🔑 API 金鑰", value=default_api_key, type="password")
        
        selected_model = None
        if api_key:
            if st.button("🔄 重新整理可用模型清單") or not st.session_state.available_models:
                with st.spinner("正在向 Google 請求可用模型..."):
                    fetch_models_callback(api_key)

            if st.session_state.available_models:
                default_idx = 0
                for i, m in enumerate(st.session_state.available_models):
                    if "gemini-3.1-pro-preview" in m.lower() or "3.1-pro" in m.lower():
                        default_idx = i
                        break
                    elif "pro-preview" in m.lower() and default_idx == 0:
                        default_idx = i
                    elif "1.5-pro" in m.lower() and default_idx == 0:
                        default_idx = i
                
                selected_model = st.selectbox("🤖 選擇運算核心 (Model)", st.session_state.available_models, index=default_idx)
                st.info(f"當前模型：{selected_model}")
            else:
                st.error("未發現可用模型，請檢查金鑰。")
                
        st.markdown("---")
        st.markdown("### 📦 模組說明速查")
        category = st.selectbox("選擇模組分類", list(modules_dict.keys()))
        for mod_name, mod_desc in modules_dict[category].items():
            with st.expander(f"🔹 {mod_name}"):
                st.caption(mod_desc)

        return api_key, selected_model

def render_chat_history(messages):
    """渲染左側歷史對話區塊"""
    st.title("Jarvis 終端控制台")
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("audio_bytes"):
                render_audio_player(msg["audio_bytes"], speed=1.8, autoplay=False)

def render_dashboard(messages):
    """渲染右側動態分析板"""
    st.subheader("📊 實時動態分析板")
    st.markdown("*(擷取自最新一輪 AI 運算結果)*")
    st.divider()
    
    latest_msg = None
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            latest_msg = msg
            break
            
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        st.markdown("**1. 啟用模組 (激活)**")
        st.info(d.get("modules", "無"))
        
        st.markdown("**2. 使用者標籤**")
        st.caption(d.get("tags", "無"))
        
        st.markdown("**3. 意圖判讀及應對策略 A**")
        st.write(d.get("intent", "無"))
        
        st.markdown("**4. 儀表板變數**")
        with st.expander(f"友善度: {d.get('friendly', 'N/A').split('(')[0]}"):
            st.write(d.get("friendly", "無資料"))
        with st.expander(f"信任度: {d.get('trust', 'N/A').split('(')[0]}"):
            st.write(d.get("trust", "無資料"))
        with st.expander(f"SAI 優勢: {d.get('sai', 'N/A').split('(')[0]}"):
            st.write(d.get("sai", "無資料"))
        with st.expander(f"準確度: {d.get('accuracy', 'N/A').split('(')[0]}"):
            st.write(d.get("accuracy", "無資料"))
            
        st.markdown("**5. SAI 修正策略**")
        with st.expander(d.get("sai_strategy", "無").split('判讀')[0]):
            st.write("**判讀理由：**", d.get("sai_reason", "無資料"))
            
        st.markdown("**6. 偽裝與準確度連動矩陣**")
        with st.expander(d.get("matrix", "無")):
            st.write("**判讀理由：**", d.get("matrix_reason", "無資料"))
            
        st.markdown("**7. 產生策略 B**")
        st.write(d.get("strategy_b", "無"))
        
        st.markdown("**8. 融合決策**")
        st.success(d.get("fusion", "無"))
        
        st.markdown("**9. 新目標 (D) / 目標庫存**")
        st.write(d.get("new_goal", "無"))
        
        st.markdown("**10. 決定次輪策略 (D)**")
        st.warning(d.get("next_strategy", "無"))
        
        st.divider()
        st.caption("⚙️ 開發者底層監控")
        with st.expander("🔍 展開底層原始運算 Log (Raw Data)", expanded=False):
            st.code(latest_msg.get("raw_text", "無資料"), language="markdown")
        
    else:
        st.caption("等待首輪對話產生運算結果...")
