# app.py
import streamlit as st

# 匯入我們自己寫的模組與運作引擎
import jarvis_config as cfg
import jarvis_engine as engine

# ==========================================
# 1. 頁面與狀態初始化
# ==========================================
st.set_page_config(page_title="Jarvis OS - Pro Edition", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

# ==========================================
# 2. 側邊欄：功能面板與模型切換
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
            selected_model = st.selectbox(
                "🤖 選擇運算核心 (Model)",
                st.session_state.available_models,
                index=0 if "gemini-1.5-pro" not in st.session_state.available_models else st.session_state.available_models.index("gemini-1.5-pro")
            )
            st.info(f"當前模型：{selected_model}")
        else:
            st.error("未發現可用模型，請檢查金鑰。")
    
    st.markdown("---")
    st.markdown("### 📦 模組說明速查")
    category = st.selectbox("選擇模組分類", list(cfg.MODULES_FOR_UI.keys()))
    st.markdown(f"**{category}**")
    for mod_name, mod_desc in cfg.MODULES_FOR_UI[category].items():
        with st.expander(f"🔹 {mod_name}"):
            st.caption(mod_desc)

# ==========================================
# 3. 主畫面：對話紀錄渲染
# ==========================================
st.title("Jarvis 終端控制台")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("internal"):
            with st.expander("🧠 展開 Jarvis 內部推演日誌 [Step 1~10]"):
                st.markdown(msg["internal"])
        elif msg["role"] == "assistant" and msg.get("raw_text"):
            with st.expander("⚠️ [除錯模式] 格式解析失敗，點此查看 AI 原始裸輸出"):
                st.code(msg["raw_text"], language="markdown")
                
        st.markdown(msg["content"])

# ==========================================
# 4. 接收輸入與呼叫運作引擎
# ==========================================
if user_input := st.chat_input("輸入指令，先生..."):
    if not api_key:
        st.error("先生，請先配置 API Key。")
        st.stop()
    
    # 畫面上只顯示乾淨的使用者輸入
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner(f'Jarvis ({selected_model}) 正在強制推演中...'):
            try:
                # 整理要傳給 API 的歷史紀錄
                history_for_api = []
                for m in st.session_state.messages[:-1]:
                    history_for_api.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})
                
                # 從設定檔取得加料的強制模板
                forced_input = cfg.get_forced_template(user_input)
                
                # 呼叫運作引擎處理一切
                result = engine.process_jarvis_turn(
                    api_key=api_key,
                    selected_model=selected_model,
                    system_prompt=cfg.SYSTEM_PROMPT,
                    history_for_api=history_for_api,
                    forced_template_text=forced_input
                )
                
                # --- 渲染輸出 ---
                if result["internal"]:
                    with st.expander("🧠 展開 Jarvis 內部推演日誌 [Step 1~10]"):
                        st.markdown(result["internal"])
                else:
                    with st.expander("⚠️ [除錯模式] 格式解析失敗，點此查看 AI 原始裸輸出"):
                        st.code(result["raw_full_text"], language="markdown")
                
                st.markdown(result["output"])
                
                # 紀錄歷史
                st.session_state.messages.append({
                    "role": "assistant",
                    "internal": result["internal"], 
                    "raw_text": result["raw_full_text"],     
                    "content": result["output"]
                })

            except Exception as e:
                st.error(f"運算中斷：{str(e)}")
