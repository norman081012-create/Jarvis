# ==========================================
# app.py
# ==========================================
import streamlit as st
import jarvis_config as cfg
import jarvis_engine as engine
from gtts import gTTS
import io
import re
from docx import Document

def generate_audio(text):
    clean = re.sub(r'[*_#`~]', '', text)
    if not clean.strip(): return None
    try:
        tts = gTTS(text=clean, lang='zh-tw')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except: return None

def create_word_export(tags, user_mem, goals):
    doc = Document()
    doc.add_heading('Jarvis Memory Bank', 0)
    sections = [
        ("24 核心維度人物卡 (Tags)", tags if tags else cfg.DEFAULT_24_TAGS), 
        ("專屬記憶 (User Memories)", user_mem), 
        ("目標庫存 (Goal Inventory)", goals)
    ]
    for title, content in sections:
        doc.add_heading(title, level=1)
        doc.add_paragraph(content if content else "Empty")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

st.set_page_config(page_title="Jarvis Command Center", layout="wide")

# 🟢 持久化記憶狀態
for key in ["messages", "available_models", "mem_user", "mem_goals"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "mem" in key else []

# 標籤預設載入 24 維度
if "mem_tags" not in st.session_state or not st.session_state.mem_tags:
    st.session_state.mem_tags = cfg.DEFAULT_24_TAGS

with st.sidebar:
    st.title("⚙️ Jarvis 控制台")
    api_key = st.text_input("🔑 API Key", value=cfg.DEFAULT_API_KEY, type="password")
    
    if api_key and (st.button("🔄 刷新模型") or not st.session_state.available_models):
        st.session_state.available_models = engine.fetch_available_models(api_key)

    if st.session_state.available_models:
        selected_model = st.selectbox("🤖 核心", st.session_state.available_models, index=0)
    
    st.markdown("---")
    st.title("🧠 記憶管理 (Memory I/O)")
    
    if st.session_state.mem_tags or st.session_state.mem_user:
        st.download_button("💾 下載記憶庫存 (.docx)", 
                           create_word_export(st.session_state.mem_tags, st.session_state.mem_user, st.session_state.mem_goals),
                           "jarvis_memory.docx")

    st.markdown("### 📥 手動覆寫專屬記憶")
    manual_mem = st.text_area("直接貼上記憶文字內容", value=st.session_state.mem_user, height=150)
    if st.button("更新專屬記憶"):
        st.session_state.mem_user = manual_mem
        st.success("記憶已更新，將於下輪生效。")

col_chat, col_dash = st.columns([6, 4], gap="large") # 微調版面比例，讓右側寬一點容納清單

with col_chat:
    st.title("Jarvis 終端")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio_bytes"): st.audio(msg["audio_bytes"], format="audio/mp3")

    if user_input := st.chat_input("輸入指令，先生..."):
        if not api_key: st.error("請輸入金鑰。"); st.stop()
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner('戰略推演中...'):
                history = []
                # 歷史訊息只傳遞純文字給 AI，減輕 Token 負擔
                for m in st.session_state.messages[:-1]:
                    role = "user" if m["role"]=="user" else "model"
                    history.append({"role": role, "parts": [m.get("raw_text", m["content"])]})
                
                forced = cfg.get_forced_template(user_input, st.session_state.mem_tags, st.session_state.mem_user, st.session_state.mem_goals)
                res = engine.process_jarvis_turn(api_key, selected_model, cfg.SYSTEM_PROMPT, history, forced)
                
                d = res["parsed_dash"]
                
                # 覆寫 24 項標籤
                if d.get("tags_inventory") and "未解析" not in d.get("tags_inventory"):
                    st.session_state.mem_tags = d["tags_inventory"]
                
                # 增量累積專屬記憶 (過濾無效輸入)
                new_fact = d.get("user_memory_delta", "")
                if new_fact and "未解析" not in new_fact and "無" not in new_fact and "[新增]" in new_fact:
                    clean_fact = new_fact.replace("[新增]", "").replace("：", "").replace(":", "").strip()
                    if clean_fact:
                        st.session_state.mem_user += f"\n- {clean_fact}"
                
                if d.get("goal_inventory") != "未解析到資料":
                    st.session_state.mem_goals = d["goal_inventory"]

                st.markdown(res["output"])
                audio = generate_audio(res["output"])
                if audio: st.audio(audio, format="audio/mp3", autoplay=True)
                
                st.session_state.messages.append({
                    "role": "assistant", "content": res["output"], "raw_text": res["raw_full_text"],
                    "parsed_dash": d, "audio_bytes": audio
                })
                st.rerun()

with col_dash:
    st.subheader("🧠 實時記憶體")
    with st.expander("📝 24 核心維度 (人物卡)", expanded=True): 
        # 使用 code block 呈現會更整齊
        st.code(st.session_state.mem_tags, language="markdown")
    with st.expander("👤 使用者專屬記憶 (累積中)", expanded=True): 
        st.write(st.session_state.mem_user if st.session_state.mem_user else "尚未累積事實記憶。")
    with st.expander("🎯 目標庫存", expanded=False): 
        st.write(st.session_state.mem_goals)
    st.divider()
    
    st.subheader("📊 戰略面板")
    last = next((m for m in reversed(st.session_state.messages) if m["role"]=="assistant"), None)
    if last and last.get("parsed_dash"):
        pd = last["parsed_dash"]
        st.info(f"激活模組: {pd.get('modules')}")
        st.success(f"意圖判讀: {pd.get('intent')}")
        st.warning(f"次輪策略: {pd.get('next_strategy')}")
        with st.expander("底層 Log"): st.code(last["raw_text"], language="markdown")
