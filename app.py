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

def create_word_export(tags, user_mem, goals):
    """將當前記憶庫存打包為 Word 檔"""
    doc = Document()
    doc.add_heading('Jarvis 核心記憶庫存 (Memory Bank)', 0)
    
    doc.add_heading('1. 標籤與特質庫存', level=1)
    doc.add_paragraph(tags if tags else "無資料")
    
    doc.add_heading('2. 使用者專屬記憶', level=1)
    doc.add_paragraph(user_mem if user_mem else "無資料")
    
    doc.add_heading('3. 目標庫存與策略', level=1)
    doc.add_paragraph(goals if goals else "無資料")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ==========================================
# 1. 頁面與狀態初始化
# ==========================================
st.set_page_config(page_title="Jarvis Command Center", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

# 記憶庫存狀態 (跨回合持久化)
if "mem_tags" not in st.session_state:
    st.session_state.mem_tags = ""
if "mem_user" not in st.session_state:
    st.session_state.mem_user = ""
if "mem_goals" not in st.session_state:
    st.session_state.mem_goals = ""

# ==========================================
# 2. 側邊欄：API、模型鎖定與記憶管理
# ==========================================
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
                if "pro-preview" in m or "3.1-pro" in m:
                    default_idx = i
                    break
                elif "1.5-pro" in m:
                    default_idx = i
            
            selected_model = st.selectbox("🤖 選擇運算核心 (Model)", st.session_state.available_models, index=default_idx)
            st.info(f"當前模型：{selected_model}")
        else:
            st.error("未發現可用模型，請檢查金鑰。")
            
    st.markdown("---")
    st.title("🧠 記憶庫存管理 (Memory I/O)")
    
    # 檔案上傳：覆寫記憶
    uploaded_mem = st.file_uploader("📥 覆寫記憶 (上傳 .txt 檔)", type=["txt"])
    if uploaded_mem is not None:
        try:
            content = uploaded_mem.read().decode("utf-8")
            if st.button("確認覆寫當前專屬記憶"):
                st.session_state.mem_user = content
                st.success("記憶覆寫成功！將於次輪注入。")
        except Exception as e:
            st.error("讀取失敗。")
            
    # 下載 Word 檔
    if st.session_state.mem_tags or st.session_state.mem_user or st.session_state.mem_goals:
        word_bytes = create_word_export(
            st.session_state.mem_tags, 
            st.session_state.mem_user, 
            st.session_state.mem_goals
        )
        st.download_button(
            label="💾 下載當前記憶庫存 (.docx)",
            data=word_bytes,
            file_name="jarvis_memory_bank.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
            
    st.markdown("---")
    st.markdown("### 📦 模組說明速查")
    category = st.selectbox("選擇模組分類", list(cfg.MODULES_FOR_UI.keys()))
    for mod_name, mod_desc in cfg.MODULES_FOR_UI[category].items():
        with st.expander(f"🔹 {mod_name}"):
            st.caption(mod_desc)

# ==========================================
# 3. 雙欄式主畫面：左側對話區
# ==========================================
col_chat, col_dash = st.columns([7, 3], gap="large")

with col_chat:
    st.title("Jarvis 終端控制台")
    
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("audio_bytes"):
                st.audio(msg["audio_bytes"], format="audio/mp3")

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
                            
                    # 🟢 動態注入當前記憶狀態至強制模板
                    forced_input = cfg.get_forced_template(
                        user_input=user_input,
                        current_tags=st.session_state.mem_tags,
                        current_user_mem=st.session_state.mem_user,
                        current_goals=st.session_state.mem_goals
                    )
                    
                    result = engine.process_jarvis_turn(
                        api_key=api_key,
                        selected_model=selected_model,
                        system_prompt=cfg.SYSTEM_PROMPT,
                        history_for_api=history_for_api,
                        forced_template_text=forced_input
                    )
                    
                    # 🟢 即時更新記憶體狀態
                    d = result["parsed_dash"]
                    if d.get("tags_inventory") and d["tags_inventory"] != "未解析到資料":
                        st.session_state.mem_tags = d["tags_inventory"]
                    if d.get("user_memory") and d["user_memory"] != "未解析到資料":
                        st.session_state.mem_user = d["user_memory"]
                    if d.get("goal_inventory") and d["goal_inventory"] != "未解析到資料":
                        st.session_state.mem_goals = d["goal_inventory"]
                    
                    st.markdown(result["output"])
                    
                    audio_bytes = generate_audio(result["output"])
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    
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

# ==========================================
# 4. 右側欄：即時戰略分析板與記憶體 (Dashboard)
# ==========================================
with col_dash:
    st.subheader("🧠 系統實時記憶體")
    with st.expander("📝 標籤與特質庫存", expanded=True):
        st.write(st.session_state.mem_tags if st.session_state.mem_tags else "空")
    with st.expander("👤 使用者專屬記憶", expanded=True):
        st.write(st.session_state.mem_user if st.session_state.mem_user else "空")
    with st.expander("🎯 目標庫存與策略", expanded=True):
        st.write(st.session_state.mem_goals if st.session_state.mem_goals else "空")
        
    st.divider()

    st.subheader("📊 實時動態分析板")
    st.markdown("*(擷取自最新一輪 AI 運算結果)*")
    
    latest_msg = None
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            latest_msg = msg
            break
            
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        st.markdown("**1. 啟用模組 (激活)**")
        st.info(d.get("modules", "無"))
        
        st.markdown("**2. 意圖判讀及應對策略 A**")
        st.write(d.get("intent", "無"))
        
        st.markdown("**3. 儀表板變數**")
        with st.expander(f"友善度: {d.get('friendly', 'N/A').split('(')[0]}"):
            st.write(d.get("friendly", "無資料"))
        with st.expander(f"信任度: {d.get('trust', 'N/A').split('(')[0]}"):
            st.write(d.get("trust", "無資料"))
        with st.expander(f"SAI 優勢: {d.get('sai', 'N/A').split('(')[0]}"):
            st.write(d.get("sai", "無資料"))
        with st.expander(f"準確度: {d.get('accuracy', 'N/A').split('(')[0]}"):
            st.write(d.get("accuracy", "無資料"))
            
        st.markdown("**4. SAI 修正策略**")
        with st.expander(d.get("sai_strategy", "無").split('判讀')[0]):
            st.write("**判讀理由：**", d.get("sai_reason", "無資料"))
            
        st.markdown("**5. 偽裝與準確度連動矩陣**")
        with st.expander(d.get("matrix", "無")):
            st.write("**判讀理由：**", d.get("matrix_reason", "無資料"))
            
        st.markdown("**6. 產生策略 B**")
        st.write(d.get("strategy_b", "無"))
        
        st.markdown("**7. 融合決策**")
        st.success(d.get("fusion", "無"))
        
        st.markdown("**8. 決定次輪策略**")
        st.warning(d.get("next_strategy", "無"))
        
        st.divider()
        st.caption("⚙️ 開發者底層監控")
        with st.expander("🔍 展開底層原始運算 Log (Raw Data)", expanded=False):
            st.code(latest_msg.get("raw_text", "無資料"), language="markdown")
        
    else:
        st.caption("等待首輪對話產生運算結果...")
