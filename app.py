# ==========================================
# app.py 
# ==========================================
import streamlit as st
import streamlit.components.v1 as components 
import base64                                
import jarvis_config as cfg
import jarvis_engine as engine
import jarvis_qa                           
from gtts import gTTS
import io
import re

def generate_audio(text):
    clean_text = re.sub(r'[*_#`~]', '', text)
    if not clean_text.strip(): return None
    try:
        tts = gTTS(text=clean_text, lang='zh-TW')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        return None

def render_audio_player(audio_bytes, autoplay=False):
    if not audio_bytes: return
    b64 = base64.b64encode(audio_bytes).decode()
    auto_attr = "autoplay" if autoplay else ""
    html_code = f"""
        <audio id="jarvis_audio_{str(hash(audio_bytes))[-5:]}" controls {auto_attr} style="width: 100%; height: 40px;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    components.html(html_code, height=50)

st.set_page_config(page_title="Jarvis Core", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "quick_input" not in st.session_state:
    st.session_state.quick_input = None

# 【新增】動態按鈕記憶庫 (預設為這三題)
if "dynamic_questions" not in st.session_state:
    st.session_state.dynamic_questions = [
        "什麼是共生政體 (Symbiocracy)？",
        "S、R、A 系統分別代表什麼？",
        "Swap 換位機制如何防範政黨擺爛？"
    ]

with st.sidebar:
    st.title("⚙️ 系統核心控制")
    
    api_key = st.text_input("🔑 API 金鑰 (安全性輸入)", type="password")
    selected_model = "gemini-1.5-flash"

    if api_key:
        if st.button("🔄 刷新模型") or not st.session_state.available_models:
            st.session_state.available_models = engine.fetch_available_models(api_key)
        if st.session_state.available_models:
            default_idx = next((i for i, m in enumerate(st.session_state.available_models) if "flash" in m.lower()), 0)
            selected_model = st.selectbox("🤖 運算核心", st.session_state.available_models, index=default_idx)

    if st.button("🗑️ 清空並重置對話"):
        st.session_state.messages = []
        st.session_state.last_audio_hash = None 
        # 重置時也恢復預設按鈕
        st.session_state.dynamic_questions = [
            "什麼是共生政體 (Symbiocracy)？",
            "S、R、A 系統分別代表什麼？",
            "Swap 換位機制如何防範政黨擺爛？"
        ]
        st.rerun()

    st.divider()
    
    st.markdown("### 🎯 當前戰略優先目標")
    priority_goal = st.selectbox(
        "選擇優先目標",
        ["解釋 symbiocracy", "經濟收入", "提升知識", "陪伴", "健康", "圓導向"],
        index=0 
    )
    st.caption("*(可被系統自動偵測之「圓導向」覆寫)*")

    st.markdown("### 📦 動態戰術模組掛載")
    all_modules_list = [mod for cat in cfg.MODULES_FOR_UI.values() for mod in cat.keys()]
    selected_modules = st.multiselect(
        "選擇要啟用或移除的模組", 
        all_modules_list, 
        default=all_modules_list 
    )

col_chat, col_dash = st.columns([6, 4], gap="large")

with col_chat:
    st.title("🎙️ Jarvis 終端")
    st.caption("開啟麥克風，或輸入文字，我隨時都在這裡聽你說。")
    
    # 【修改】動態渲染三個引導按鈕
    st.markdown("💡 **快速引導發問：**")
    cols = st.columns(3)
    for i, q in enumerate(st.session_state.dynamic_questions[:3]):
        # 防呆，確保有按鈕文字才渲染
        if q.strip(): 
            if cols[i].button(q, key=f"dyn_btn_{i}"):
                st.session_state.quick_input = q
    st.markdown("---")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("audio_bytes"):
                render_audio_player(msg["audio_bytes"], autoplay=False)

    audio_val = st.audio_input("語音指令...")
    text_val = st.chat_input("或輸入文字指令...")
    
    need_process = False
    is_audio = False
    
    if st.session_state.quick_input:
        text_val = st.session_state.quick_input
        st.session_state.quick_input = None 
        need_process = True
    elif text_val:
        need_process = True
    elif audio_val:
        current_audio_hash = hash(audio_val.getvalue())
        if current_audio_hash != st.session_state.last_audio_hash:
            need_process = True
            is_audio = True
            st.session_state.last_audio_hash = current_audio_hash

    if need_process:
        if not api_key:
            st.error("⚠️ 先生，請先於左側面板輸入您的 API 金鑰。")
            st.stop()
            
        display_text = "*(接收到語音訊號)*" if is_audio else text_val
        
        st.session_state.messages.append({"role": "user", "content": display_text})
        with st.chat_message("user"):
            st.markdown(display_text)

        with st.chat_message("assistant"):
            with st.spinner('運算推演中...'):
                history_for_api = [{"role": m["role"], "parts": [m.get("raw_text", m["content"])]} for m in st.session_state.messages[:-1]]
                forced_input = cfg.get_forced_template(text_val if text_val else "請分析語音內容。")
                
                audio_data = {"mime_type": "audio/wav", "data": audio_val.getvalue()} if is_audio else None
                
                is_sym = jarvis_qa.is_symbiocracy_related(text_val) if text_val else False
                dynamic_prompt = cfg.get_system_prompt(priority_goal, selected_modules, is_sym)
                
                result = engine.process_jarvis_turn(api_key, selected_model, dynamic_prompt, history_for_api, forced_input, audio_data)
                
                output_text = result["output"]
                
                # 【新增】攔截並抽離動態提問
                # 尋找 "💡 **快速引導發問：**" 後面的所有項目符號
                match = re.search(r'💡 \*\*快速引導發問：\*\*\n(.*?)(?:\Z)', output_text, re.DOTALL)
                if match:
                    # 抓出星號或減號開頭的句子
                    bullets = re.findall(r'[\*\-]\s*([^\n]+)', match.group(1))
                    if len(bullets) > 0:
                        # 用新抓到的問題覆蓋舊問題，不夠三個就拿舊的補
                        new_qs = (bullets + st.session_state.dynamic_questions)[:3]
                        st.session_state.dynamic_questions = new_qs
                        
                    # 從給使用者的畫面上把這段文字「喀嚓」剪掉，保持乾淨
                    output_text = output_text[:match.start()].strip()
                    result["output"] = output_text

                st.markdown(result["output"])
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
    st.divider()
    
    latest_msg = next((msg for msg in reversed(st.session_state.messages) if msg["role"] == "assistant"), None)
            
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("生物算力殘留", d.get('bio_compute', 'N/A').split('(')[0])
            st.metric("SAI 社交優勢", d.get('sai', 'N/A').split('(')[0])
        with col2:
            st.metric("全知偽裝級別", d.get('matrix', 'N/A'))
            st.metric("當前準確度", d.get('accuracy', 'N/A').split('(')[0])
            
        st.markdown("**📍 拓撲座標判定**")
        st.caption(f"位置: {d.get('location', '無')} / 變化: {d.get('trend', '無')}")
        
        st.markdown("**📦 當前結算庫存**")
        st.info(d.get("tags", "無"))
        
        st.markdown("**🧠 意圖判讀與策略**")
        st.write(d.get("intent", "無"))
        with st.expander("SAI 修正策略"):
            st.write(d.get("sai_strategy", "無"))
            
        st.markdown("**⚖️ 最終融合決策**")
        st.success(d.get("fusion", "無"))
        
        st.markdown("**🎯 次輪引導準備**")
        st.warning(f"新目標: {d.get('new_goal', '無')}")
        st.caption(f"次輪策略: {d.get('next_strategy', '無')}")
        
        st.divider()
        with st.expander("🔍 展開底層原始運算 (Raw Data)", expanded=False):
            st.code(latest_msg.get("raw_text", "無資料"), language="markdown")
    else:
        st.caption("等待啟動...")
