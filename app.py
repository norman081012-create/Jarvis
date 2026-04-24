# app.py
import streamlit as st
import jarvis_config as cfg
import jarvis_engine as engine

# ==========================================
# 1. 頁面與狀態初始化 (改用超寬版面)
# ==========================================
st.set_page_config(page_title="Jarvis Command Center", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

# ==========================================
# 2. 側邊欄：API 與模型鎖定 (優先選 pro-preview)
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
            # 優先尋找名稱包含 pro-preview 或 3.1-pro 的模型，找不到再退回 1.5-pro
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
    st.markdown("### 📦 模組說明速查")
    category = st.selectbox("選擇模組分類", list(cfg.MODULES_FOR_UI.keys()))
    for mod_name, mod_desc in cfg.MODULES_FOR_UI[category].items():
        with st.expander(f"🔹 {mod_name}"):
            st.caption(mod_desc)

# ==========================================
# 3. 雙欄式主畫面：左側對話區 / 右側即時分析板
# ==========================================
col_chat, col_dash = st.columns([7, 3], gap="large")

with col_chat:
    st.title("Jarvis 終端控制台")
    
    # 渲染歷史對話
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # 將原始 Log 藏在最不顯眼的地方 (字體縮小、預設關閉)
            if msg.get("internal"):
                with st.expander("🔍 查看底層原始運算 Log (Raw Data)"):
                    st.caption(msg["internal"].replace('\n', '  \n')) # caption 會讓字體變小變灰
            elif msg["role"] == "assistant" and msg.get("raw_text"):
                with st.expander("⚠️ [除錯模式] 格式解析失敗，原始裸輸出"):
                    st.code(msg["raw_text"], language="markdown")

    # 接收輸入與呼叫運作引擎
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
                    history_for_api = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                    forced_input = cfg.get_forced_template(user_input)
                    
                    result = engine.process_jarvis_turn(
                        api_key=api_key,
                        selected_model=selected_model,
                        system_prompt=cfg.SYSTEM_PROMPT,
                        history_for_api=history_for_api,
                        forced_template_text=forced_input
                    )
                    
                    st.markdown(result["output"])
                    
                    # 藏起原始 Log
                    if result["internal"]:
                        with st.expander("🔍 查看底層原始運算 Log (Raw Data)"):
                            st.caption(result["internal"].replace('\n', '  \n'))
                    else:
                        with st.expander("⚠️ [除錯模式] 格式解析失敗，原始裸輸出"):
                            st.code(result["raw_full_text"], language="markdown")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "internal": result["internal"], 
                        "raw_text": result["raw_full_text"],     
                        "content": result["output"],
                        "parsed_dash": result["parsed_dash"] # 存入解析後的儀表板數據
                    })
                    st.rerun() # 強制刷新畫面，讓右側面板更新

                except Exception as e:
                    st.error(f"運算中斷：{str(e)}")

# ==========================================
# 4. 右側欄：即時戰略分析板 (Dashboard)
# ==========================================
with col_dash:
    st.subheader("📊 實時動態分析板")
    st.markdown("*(擷取自最新一輪 AI 運算結果)*")
    st.divider()
    
    # 找尋最後一筆擁有解析資料的 assistant 訊息
    latest_data = {}
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and msg.get("parsed_dash"):
            latest_data = msg["parsed_dash"]
            break
            
    if latest_data:
        d = latest_data
        
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
        
    else:
        st.caption("等待首輪對話產生運算結果...")
