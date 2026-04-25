# ==========================================
# app.py
# ==========================================
import streamlit as st
import streamlit.components.v1 as components
import jarvis_config as cfg
import jarvis_engine as engine
from gtts import gTTS
import io
import re
import base64
from docx import Document

# ==========================================
# 語音與文件輔助函數
# ==========================================
def generate_audio_bytes(text):
    clean = re.sub(r'[*_#`~]', '', text)
    if not clean.strip(): return None
    try:
        tts = gTTS(text=clean, lang='zh-tw')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except: 
        return None

def render_audio_player(audio_bytes, speed=1.25, autoplay=False):
    """利用前端 HTML/JS 強制改變語音播放速度"""
    if not audio_bytes: return
    b64 = base64.b64encode(audio_bytes).decode()
    auto_attr = "autoplay" if autoplay else ""
    html_code = f"""
        <audio id="jarvis_audio" controls {auto_attr} style="width: 100%; height: 40px;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
            var audio = document.getElementById("jarvis_audio");
            audio.playbackRate = {speed};
        </script>
    """
    components.html(html_code, height=50)

# (匯出 Word 函數略，請沿用上一版的 create_word_export)
def create_word_export(tags, user_mem, goals):
    doc = Document()
    doc.add_heading('Jarvis Memory Bank', 0)
    sections = [
        ("24 核心維度 (Tags)", tags if tags else cfg.DEFAULT_24_TAGS), 
        ("專屬記憶 (Memories)", user_mem), 
        ("目標庫存 (Goals)", goals)
    ]
    for title, content in sections:
        doc.add_heading(title, level=1)
        doc.add_paragraph(content if content else "Empty")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

st.set_page_config(page_title="Jarvis Command Center", layout="wide")

for key in ["messages", "available_models", "mem_user", "mem_goals"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "mem" in key else []

if "mem_tags" not in st.session_state or not st.session_state.mem_tags:
    st.session_state.mem_tags = cfg.DEFAULT_24_TAGS

# ==========================================
# 2. 側邊欄：控制台
# ==========================================
with st.sidebar:
    st.title("⚙️ Jarvis 控制台")
    api_key = st.text_input("🔑 API Key", value=cfg.DEFAULT_API_KEY, type="password")
    
    if api_key and (st.button("🔄 刷新模型") or not st.session_state.available_models):
        st.session_state.available_models = engine.fetch_available_models(api_key)

    if st.session_state.available_models:
        default_idx = next((i for i, m in enumerate(st.session_state.available_models) if "3.1-pro" in m.lower()), 0)
        selected_model = st.selectbox("🤖 運算核心", st.session_state.available_models, index=default_idx)
    
    st.markdown("---")
    # 🟢 新增：語速控制拉桿
    st.subheader("🗣️ 語音設定")
    playback_speed = st.slider("朗讀倍速 (預設 1.3x)", min_value=1.0, max_value=2.0, value=1.3, step=0.1)
    
    st.markdown("---")
    st.title("🧠 記憶管理 (Memory I/O)")
    if st.session_state.mem_tags or st.session_state.mem_user:
        st.download_button("💾 下載記憶庫存 (.docx)", 
                           create_word_export(st.session_state.mem_tags, st.session_state.mem_user, st.session_state.mem_goals),
                           "jarvis_memory.docx")

# ==========================================
# 3. 主畫面
# ==========================================
col_chat, col_dash = st.columns([6, 4], gap="large") 

with col_chat:
    st.title("Jarvis 終端")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # 套用新版倍速播放器
            if msg.get("audio_bytes"): 
                render_audio_player(msg["audio_bytes"], speed=playback_speed, autoplay=False)

    if user_input := st.chat_input("輸入指令，先生..."):
        if not api_key: st.stop()
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner(f'Jarvis 戰略推演中...'):
                try:
                    history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m.get("raw_text", m["content"])]} for m in st.session_state.messages[:-1]]
                    forced = cfg.get_forced_template(user_input, st.session_state.mem_tags, st.session_state.mem_user, st.session_state.mem_goals)
                    
                    res = engine.process_jarvis_turn(api_key, selected_model, cfg.SYSTEM_PROMPT, history, forced)
                    d = res["parsed_dash"]
                    
                    if d.get("tags_inventory") and "未解析" not in d.get("tags_inventory"):
                        st.session_state.mem_tags = d["tags_inventory"]
                    
                    new_fact = d.get("user_memory_delta", "")
                    if new_fact and "未解析" not in new_fact and "無" not in new_fact:
                        clean_fact = new_fact.replace("[新增]", "").replace("：", "").strip()
                        if clean_fact: st.session_state.mem_user += f"\n- {clean_fact}"
                    
                    if d.get("goal_inventory") and "未解析" not in d.get("goal_inventory"):
                        st.session_state.mem_goals = d["goal_inventory"]

                    st.markdown(res["output"])
                    
                    # 生成音檔並用 HTML 播放器（自動播放，套用側邊欄倍速）
                    audio = generate_audio_bytes(res["output"])
                    if audio: 
                        render_audio_player(audio, speed=playback_speed, autoplay=True)
                    
                    st.session_state.messages.append({
                        "role": "assistant", "content": res["output"], "raw_text": res["raw_full_text"],
                        "parsed_dash": d, "audio_bytes": audio
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"運算中斷：{str(e)}")

with col_dash:
    st.subheader("🧠 系統實時記憶體")
    with st.expander("📝 24 核心維度 (人物卡)", expanded=True): st.code(st.session_state.mem_tags, language="markdown")
    with st.expander("👤 使用者專屬記憶", expanded=True): st.write(st.session_state.mem_user if st.session_state.mem_user.strip() else "尚未累積。")
    with st.expander("🎯 目標庫存與策略", expanded=False): st.write(st.session_state.mem_goals)
    st.divider()
    
    st.subheader("📊 動態戰略面板")
    last = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    if last and last.get("parsed_dash"):
        pd = last["parsed_dash"]
        st.info(f"**激活模組**\n\n{pd.get('modules', '無')}")
        st.success(f"**意圖判讀 A**\n\n{pd.get('intent', '無')}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SAI 優勢", pd.get('sai', 'N/A')[:3])
        c2.metric("友善度", pd.get('friendly', 'N/A')[:3])
        c3.metric("信任度", pd.get('trust', 'N/A')[:3])
        c4.metric("準確度", pd.get('accuracy', 'N/A')[:3])
        
        st.warning(f"**次輪策略**\n\n{pd.get('next_strategy', '無')}")
        
        st.divider()
        with st.expander("🔍 展開底層原始推演 Log", expanded=False): st.code(last["raw_text"], language="markdown")
