# ==========================================
# app.py
# ==========================================
import streamlit as st
import streamlit.components.v1 as components 
import base64                                
import jarvis_config as cfg
import jarvis_engine as engine
from gtts import gTTS
import io
import re

def generate_audio(text):
    clean_text = re.sub(r'[*_#`~]', '', text)
    if not clean_text.strip(): return None
    try:
        tts = gTTS(text=clean_text, lang='zh-tw')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.error(f"語音生成失敗: {e}")
        return None

def render_audio_player(audio_bytes, speed=1.8, autoplay=False):
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

st.set_page_config(page_title="Jarvis Command Center", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

with st.sidebar:
    st.title("⚙️ Jarvis 系統控制")
    api_key = st.text_input("🔑 API 金鑰", value=cfg.DEFAULT_API_KEY, type="password")
    
    if api_key:
        if st.button("🔄 重新整理可用模型清單") or not st.session_state.available_models:
            with st.spinner("正在向 Google 請求可用模型..."):
                try:
                    st.session_state.available_models = engine.fetch_available_models(api_key)
                except Exception as e:
                    st.error(f"無法獲取清單: {e}")

        if st.session_state.available_models:
            default_idx = 0
            for i, m in enumerate(st.session_state.available_models):
                if "gemini-3.1-pro-preview" in m.lower() or "3.1-pro" in m.lower():
                    default_idx = i; break
                elif "pro-preview" in m.lower() and default_idx == 0: default_idx = i
                elif "1.5-pro" in m.lower() and default_idx == 0: default_idx = i
            
            selected_model = st.selectbox("🤖 選擇運算核心 (Model)", st.session_state.available_models, index=default_idx)
            st.info(f"當前模型：{selected_model}")
        else:
            st.error("未發現可用模型，請檢查金鑰。")
            
    st.markdown("---")
    # 🔥 新增：偏好目標選擇器
    st.markdown("### 🎯 戰略引導目標")
    preferred_goal = st.selectbox("偏好預設目標 (Idle 接管)", ["經濟收入", "提升知識", "陪伴", "健康", "圓導向"], index=0)
    st.caption("AI 在您未明確指示時，將自動朝此目標收束。")

    st.markdown("---")
    st.markdown("### 📦 模組說明速查")
    category = st.selectbox("選擇模組分類", list(cfg.MODULES_FOR_UI.keys()))
    for mod_name, mod_desc in cfg.MODULES_FOR_UI[category].items():
        with st.expander(f"🔹 {mod_name}"):
            st.caption(mod_desc)

col_chat, col_dash = st.columns([7, 3], gap="large")

with col_chat:
    st.title("Jarvis 終端控制台")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("audio_bytes"):
                render_audio_player(msg["audio_bytes"], speed=1.8, autoplay=False)

    if user_input := st.chat_input("輸入指令，先生..."):
        if not api_key:
            st.error("先生，請先配置 API Key。")
            st.stop()
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner(f'Jarvis ({selected_model}) 戰略推演中...'):
                try:
                    history_for_api = []
                    for m in st.session_state.messages[:-1]:
                        if m["role"] == "user":
                            history_for_api.append({"role": "user", "parts": [m["content"]]})
                        else:
                            full_memory = m.get("raw_text", m["content"])
                            history_for_api.append({"role": "model", "parts": [full_memory]})
                            
                    forced_input = cfg.get_forced_template(user_input)
                    
                    # 🔥 更新：動態傳入使用者選擇的偏好目標
                    result = engine.process_jarvis_turn(
                        api_key=api_key,
                        selected_model=selected_model,
                        system_prompt=cfg.get_system_prompt(preferred_goal), 
                        history_for_api=history_for_api,
                        forced_template_text=forced_input
                    )
                    
                    st.markdown(result["output"])
                    
                    audio_bytes = generate_audio(result["output"])
                    if audio_bytes:
                        render_audio_player(audio_bytes, speed=1.8, autoplay=True)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "raw_text": result["raw_full_text"],     
                        "content": result["output"],
                        "parsed_dash": result["parsed_dash"],
                        "audio_bytes": audio_bytes 
                    })
                    st.rerun() 

                except Exception as e:
                    st.error(f"運算中斷：{str(e)}")

with col_dash:
    st.subheader("📊 實時動態分析板")
    st.markdown("*(擷取自最新一輪 AI 運算結果)*")
    st.divider()
    
    latest_msg = None
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            latest_msg = msg
            break
            
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        st.markdown("**1. 啟用模組 (激活)**")
        st.info(d.get("modules", "無"))
        
        st.markdown("**2. 使用者標籤 / 庫存**")
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
        
        st.markdown("**9. 新目標 (D)**")
        st.write(d.get("new_goal", "無"))
        
        st.markdown("**10. 決定次輪策略 (D)**")
        st.warning(d.get("next_strategy", "無"))
        
        st.divider()
        st.caption("⚙️ 開發者底層監控")
        with st.expander("🔍 展開底層原始運算 Log (Raw Data)", expanded=False):
            st.code(latest_msg.get("raw_text", "無資料"), language="markdown")
        
    else:
        st.caption("等待首輪對話產生運算結果...")
