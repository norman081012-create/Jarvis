# ==========================================
# app.py
# 主程式控制層 (Controller)：狀態管理與模組調度
# ==========================================
import streamlit as st
import jarvis_prompt as jp
import jarvis_engine as engine
import jarvis_ui as ui
from gtts import gTTS
import io
import re

# ==========================================
# 工具邏輯 (TTS 生成)
# ==========================================
def generate_audio(text):
    """將文字轉換為語音並返回 Byte 數據"""
    clean_text = re.sub(r'[*_#`~]', '', text)
    if not clean_text.strip():
        return None
    try:
        tts = gTTS(text=clean_text, lang='zh-tw')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.error(f"語音生成失敗: {e}")
        return None

# ==========================================
# 狀態初始化與回呼函數
# ==========================================
ui.setup_page()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

def fetch_models_callback(api_key):
    """供 UI 呼叫的回呼函數：更新可用模型清單"""
    try:
        st.session_state.available_models = engine.fetch_available_models(api_key)
    except Exception as e:
        st.error(f"無法獲取清單: {e}")

# ==========================================
# 主畫面流與調度
# ==========================================
# 1. 渲染側邊欄取得參數 (已修正為從 ui 讀取常數)
api_key, selected_model = ui.render_sidebar(
    default_api_key=ui.DEFAULT_API_KEY, 
    modules_dict=ui.MODULES_FOR_UI, 
    fetch_models_callback=fetch_models_callback
)

# 2. 建立雙欄位佈局
col_chat, col_dash = st.columns([7, 3], gap="large")

# 3. 控制左側聊天區邏輯
with col_chat:
    ui.render_chat_history(st.session_state.messages)

    if user_input := st.chat_input("輸入指令，先生..."):
        if not api_key:
            st.error("先生，請先配置 API Key。")
            st.stop()
        
        # 寫入使用者對話
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # AI 運算區塊
        with st.chat_message("assistant"):
            with st.spinner(f'Jarvis ({selected_model}) 戰略推演中...'):
                try:
                    # 整理傳給 API 的歷史記憶 (強迫 AI 看見自己的底層推演)
                    history_for_api = []
                    for m in st.session_state.messages[:-1]:
                        if m["role"] == "user":
                            history_for_api.append({"role": "user", "parts": [m["content"]]})
                        else:
                            full_memory = m.get("raw_text", m["content"])
                            history_for_api.append({"role": "model", "parts": [full_memory]})
                            
                    forced_input = jp.get_forced_template(user_input)
                    
                    # 呼叫運算引擎
                    result = engine.process_jarvis_turn(
                        api_key=api_key,
                        selected_model=selected_model,
                        system_prompt=jp.SYSTEM_PROMPT,
                        history_for_api=history_for_api,
                        forced_template_text=forced_input
                    )
                    
                    # 輸出回答
                    st.markdown(result["output"])
                    
                    # 生成並播放音檔
                    audio_bytes = generate_audio(result["output"])
                    if audio_bytes:
                        ui.render_audio_player(audio_bytes, speed=1.8, autoplay=True)
                    
                    # 儲存本輪狀態
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

# 4. 渲染右側儀表板
with col_dash:
    ui.render_dashboard(st.session_state.messages)
