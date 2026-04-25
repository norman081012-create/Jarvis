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

# ==========================================
# 語音與文件輔助函數
# ==========================================
def generate_audio(text):
    clean = re.sub(r'[*_#`~]', '', text)
    if not clean.strip(): return None
    try:
        tts = gTTS(text=clean, lang='zh-tw')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e: 
        # 靜默處理語音錯誤，避免干擾 UI
        return None

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

# ==========================================
# 1. 頁面與狀態初始化
# ==========================================
st.set_page_config(page_title="Jarvis Command Center", layout="wide")

# 🟢 持久化記憶與對話狀態
for key in ["messages", "available_models", "mem_user", "mem_goals"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "mem" in key else []

# 標籤預設載入 24 維度
if "mem_tags" not in st.session_state or not st.session_state.mem_tags:
    st.session_state.mem_tags = cfg.DEFAULT_24_TAGS

# ==========================================
# 2. 側邊欄：API、模型鎖定與記憶管理
# ==========================================
with st.sidebar:
    st.title("⚙️ Jarvis 控制台")
    api_key = st.text_input("🔑 API Key", value=cfg.DEFAULT_API_KEY, type="password")
    
    if api_key and (st.button("🔄 刷新模型清單") or not st.session_state.available_models):
        with st.spinner("獲取可用核心中..."):
            try:
                st.session_state.available_models = engine.fetch_available_models(api_key)
            except Exception as e:
                st.error(f"無法獲取清單: {e}")

    # 🟢 強化版模型鎖定邏輯：強制預設 Gemini 3.1 Pro
    if st.session_state.available_models:
        default_idx = 0
        for i, m in enumerate(st.session_state.available_models):
            # 第一優先級：3.1 Pro 相關型號
            if "3.1-pro" in m.lower() or "gemini-3.1" in m.lower():
                default_idx = i
                break
            # 第二優先級：其他 Pro 預覽版
            elif "pro-preview" in m.lower() and default_idx == 0:
                default_idx = i
            # 第三優先級：1.5 Pro
            elif "1.5-pro" in m.lower() and default_idx == 0:
                default_idx = i
        
        selected_model = st.selectbox("🤖 運算核心", st.session_state.available_models, index=default_idx)
        st.info(f"當前鎖定：{selected_model}")
    
    st.markdown("---")
    st.title("🧠 記憶管理 (Memory I/O)")
    
    # 匯出 Word 檔
    if st.session_state.mem_tags or st.session_state.mem_user:
        st.download_button("💾 下載記憶庫存 (.docx)", 
                           create_word_export(st.session_state.mem_tags, st.session_state.mem_user, st.session_state.mem_goals),
                           "jarvis_memory.docx")

    # 手動修改記憶
    st.markdown("### 📥 手動覆寫專屬記憶")
    manual_mem = st.text_area("直接貼上記憶文字內容", value=st.session_state.mem_user, height=150)
    if st.button("更新專屬記憶"):
        st.session_state.mem_user = manual_mem
        st.success("記憶已更新，將於下輪生效。")

# ==========================================
# 3. 雙欄式主畫面：對話區 (左 6) / 儀表板 (右 4)
# ==========================================
col_chat, col_dash = st.columns([6, 4], gap="large") 

# --- 左側：對話終端 ---
with col_chat:
    st.title("Jarvis 終端")
    
    # 渲染歷史對話
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio_bytes"): 
                st.audio(msg["audio_bytes"], format="audio/mp3")

    # 接收新指令
    if user_input := st.chat_input("輸入指令，先生..."):
        if not api_key: 
            st.error("先生，請先配置 API 金鑰。")
            st.stop()
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): 
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner(f'Jarvis 戰略推演中...'):
                try:
                    history = []
                    # 歷史訊息只傳遞純文字給 AI，減輕 Token 負擔
                    for m in st.session_state.messages[:-1]:
                        role = "user" if m["role"] == "user" else "model"
                        history.append({"role": role, "parts": [m.get("raw_text", m["content"])]})
                    
                    # 注入當前所有記憶體狀態
                    forced = cfg.get_forced_template(user_input, st.session_state.mem_tags, st.session_state.mem_user, st.session_state.mem_goals)
                    
                    # 啟動引擎
                    res = engine.process_jarvis_turn(api_key, selected_model, cfg.SYSTEM_PROMPT, history, forced)
                    d = res["parsed_dash"]
                    
                    # 🟢 記憶體覆寫與增量更新邏輯
                    # 1. 覆寫 24 項標籤
                    if d.get("tags_inventory") and "未解析" not in d.get("tags_inventory"):
                        st.session_state.mem_tags = d["tags_inventory"]
                    
                    # 2. 增量累積專屬記憶 (過濾無效輸入)
                    new_fact = d.get("user_memory_delta", "")
                    if new_fact and "未解析" not in new_fact and "無" not in new_fact and "[新增]" in new_fact:
                        clean_fact = new_fact.replace("[新增]", "").replace("：", "").replace(":", "").strip()
                        if clean_fact:
                            # 加上換行與 bullet point 累積
                            st.session_state.mem_user += f"\n- {clean_fact}"
                    
                    # 3. 覆寫目標庫存
                    if d.get("goal_inventory") and "未解析" not in d.get("goal_inventory"):
                        st.session_state.mem_goals = d["goal_inventory"]

                    # 顯示文字回覆
                    st.markdown(res["output"])
                    
                    # 語音生成
                    audio = generate_audio(res["output"])
                    if audio: 
                        st.audio(audio, format="audio/mp3", autoplay=True)
                    
                    # 存入 Session State
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": res["output"], 
                        "raw_text": res["raw_full_text"],
                        "parsed_dash": d, 
                        "audio_bytes": audio
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"運算中斷：{str(e)}")


# --- 右側：實時分析板 ---
with col_dash:
    st.subheader("🧠 系統實時記憶體")
    
    with st.expander("📝 24 核心維度 (人物卡)", expanded=True): 
        # 使用 code block 呈現會更整齊且固定寬度
        st.code(st.session_state.mem_tags, language="markdown")
        
    with st.expander("👤 使用者專屬記憶 (增量累積)", expanded=True): 
        st.write(st.session_state.mem_user if st.session_state.mem_user.strip() else "尚未累積事實記憶。")
        
    with st.expander("🎯 目標庫存與策略", expanded=False): 
        st.write(st.session_state.mem_goals if st.session_state.mem_goals else "空")
        
    st.divider()
    
    st.subheader("📊 動態戰略面板")
    # 抓取最後一則 AI 回覆的面板資料
    last = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    
    if last and last.get("parsed_dash"):
        pd = last["parsed_dash"]
        
        st.info(f"**激活模組**\n\n{pd.get('modules', '無')}")
        st.success(f"**意圖判讀 A**\n\n{pd.get('intent', '無')}")
        
        st.markdown("**儀表板狀態**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SAI 優勢", pd.get('sai', 'N/A')[:3])
        c2.metric("友善度", pd.get('friendly', 'N/A')[:3])
        c3.metric("信任度", pd.get('trust', 'N/A')[:3])
        c4.metric("準確度", pd.get('accuracy', 'N/A')[:3])
        
        st.warning(f"**次輪策略**\n\n{pd.get('next_strategy', '無')}")
        
        st.divider()
        st.caption("⚙️ 開發者底層監控")
        with st.expander("🔍 展開底層原始推演 Log", expanded=False): 
            st.code(last["raw_text"], language="markdown")
    else:
        st.caption("等待首輪運算數據...")
