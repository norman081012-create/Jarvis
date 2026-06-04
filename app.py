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
        # 使用 gTTS 生成溫和的中文語音
        tts = gTTS(text=clean_text, lang='zh-TW')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.error(f"語音生成失敗: {e}")
        return None

def render_audio_player(audio_bytes, autoplay=False):
    if not audio_bytes: return
    b64 = base64.b64encode(audio_bytes).decode()
    auto_attr = "autoplay" if autoplay else ""
    html_code = f"""
        <audio id="jarvis_audio_{str(hash(audio_bytes))[-5:]}" controls {auto_attr} style="width: 100%; height: 40px; border-radius: 10px;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    components.html(html_code, height=50)

st.set_page_config(page_title="Jarvis 2.0 Companion", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

with st.sidebar:
    st.title("💖 Jarvis 陪伴核心")
    api_key = st.text_input("🔑 API 金鑰", value=cfg.DEFAULT_API_KEY, type="password")
    
    if api_key:
        if st.button("🔄 刷新模型清單") or not st.session_state.available_models:
            with st.spinner("連接中..."):
                st.session_state.available_models = engine.fetch_available_models(api_key)

        if st.session_state.available_models:
            # 優先選擇具備多模態音訊處理能力的 1.5 系列
            default_idx = next((i for i, m in enumerate(st.session_state.available_models) if "1.5-pro" in m.lower()), 0)
            selected_model = st.selectbox("🤖 運算核心", st.session_state.available_models, index=default_idx)
            
    st.markdown("---")
    st.markdown("### 📦 心理陪伴模組")
    category = st.selectbox("選擇分類", list(cfg.MODULES_FOR_UI.keys()))
    for mod_name, mod_desc in cfg.MODULES_FOR_UI[category].items():
        with st.expander(f"🔹 {mod_name}"):
            st.caption(mod_desc)

col_chat, col_dash = st.columns([7, 3], gap="large")

with col_chat:
    st.title("🎙️ Jarvis 2.0")
    st.markdown("開啟麥克風，或輸入文字，我隨時都在這裡聽你說。")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("is_audio_input"):
                st.markdown("*(語音輸入)*")
            else:
                st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("audio_bytes"):
                render_audio_player(msg["audio_bytes"], autoplay=False)

    # 雙輸入支援：麥克風錄音 或 文字輸入
    audio_val = st.audio_input("對 Jarvis 說話...")
    text_val = st.chat_input("或輸入文字...")
    
    if audio_val or text_val:
        if not api_key:
            st.error("請先配置 API Key。")
            st.stop()
            
        is_audio = bool(audio_val)
        display_content = "*(已接收語音輸入)*" if is_audio else text_val
        
        st.session_state.messages.append({"role": "user", "content": text_val if text_val else "處理語音中...", "is_audio_input": is_audio})
        with st.chat_message("user"):
            st.markdown(display_content)

        with st.chat_message("assistant"):
            with st.spinner('感知情緒與運算中...'):
                history_for_api = []
                for m in st.session_state.messages[:-1]:
                    if m["role"] == "user":
                        # API 歷史不包含二進制音訊，僅保留文字脈絡
                        history_for_api.append({"role": "user", "parts": [m["content"] if not m.get("is_audio_input") else " (使用者傳送了一段語音) "]})
                    else:
                        history_for_api.append({"role": "model", "parts": [m.get("raw_text", m["content"])]})
                        
                forced_input = cfg.get_forced_template(text_val if text_val else "請分析我的語音內容，並依照 Jarvis 2.0 規範回應。")
                
                # 準備音訊資料給 Gemini API
                audio_data = None
                if is_audio:
                    audio_data = {
                        "mime_type": "audio/wav",
                        "data": audio_val.getvalue()
                    }
                
                result = engine.process_jarvis_turn(
                    api_key=api_key,
                    selected_model=selected_model,
                    system_prompt=cfg.get_system_prompt(), 
                    history_for_api=history_for_api,
                    forced_template_text=forced_input,
                    audio_data=audio_data
                )
                
                st.markdown(result["output"])
                
                # 輸出 TTS 語音
                out_audio = generate_audio(result["output"])
                if out_audio:
                    render_audio_player(out_audio, autoplay=True)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "raw_text": result["raw_full_text"],     
                    "content": result["output"],
                    "parsed_dash": result["parsed_dash"],
                    "audio_bytes": out_audio 
                })
                st.rerun() 

with col_dash:
    st.subheader("📊 心理狀態監測板")
    st.markdown("*(即時渲染自情緒運算矩陣)*")
    st.divider()
    
    latest_msg = next((msg for msg in reversed(st.session_state.messages) if msg["role"] == "assistant"), None)
            
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        # 使用全新 Jarvis 2.0 變數渲染
        st.error(f"⚠️ 防衛機制計數: {d.get('defense', 'N/A')}")
        st.warning(f"🌡️ 情緒負荷判定: {d.get('overload', 'N/A')}")
        
        st.markdown("**1. 啟用模組**")
        st.info(d.get("modules", "無"))
        
        st.markdown("**2. 心理標籤庫存**")
        st.caption(d.get("tags", "無"))
        
        st.markdown("**3. 意圖與陪伴策略**")
        st.write(d.get("intent", "無"))
        
        st.markdown("**4. 情感儀表板**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("共情度", d.get('empathy', 'N/A').split('(')[0])
            st.metric("信任度", d.get('trust', 'N/A').split('(')[0])
        with col2:
            st.metric("SAI姿態", d.get('sai_pose', 'N/A').split('(')[0])
            st.metric("算力殘留", d.get('emotional_compute', 'N/A').split('(')[0])
            
        st.markdown("**5. 最終陪伴融合決策**")
        st.success(d.get("fusion", "無"))
        
        st.markdown("**6. 隱性引導目標**")
        st.write(d.get("new_goal", "無"))
        
        st.divider()
        with st.expander("🔍 展開底層原始運算 (Raw Data)", expanded=False):
            st.code(latest_msg.get("raw_text", "無資料"), language="markdown")
    else:
        st.caption("等待您訴說...")
