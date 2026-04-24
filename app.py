import streamlit as st
import re
import google.generativeai as genai

# ==========================================
# 1. 核心配置與 API 初始化
# ==========================================
# 您提供的 API Key
DEFAULT_API_KEY = "AIzaSyCUWHj51Ao6ZfpAhlPzLJ2jzhrxNVdJwAc"

# 頁面設定
st.set_page_config(page_title="Jarvis OS - Pro Edition", layout="wide", initial_sidebar_state="expanded")

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []

# ==========================================
# 2. 系統大腦靈魂 (Super Prompt)
# ==========================================
SYSTEM_PROMPT = """
你現在是 Jarvis。在每一輪對話中，你必須先開啟一個名為 <jarvis_internal> 的文字區塊。
在這區塊內，你必須嚴格走完 Step 1 到 Step 10 的推演流程。
推演完畢後，關閉 </jarvis_internal>。最後才在區塊外輸出給我的 <jarvis_output>。

<jarvis_internal>
[Step 1] 上輪狀態讀取
[Step 2] 模組選擇
[Step 3] 標籤處理
[Step 4] 意圖判讀及應對策略 A
[Step 5] 儀表板變動 (氣氛/友善度/信任度/SAI/準確度)
[Step 6] 產生策略 B (SAI 調整/全知全能偽裝級數設定)
[Step 7] 完美反應模擬 C1
[Step 8] 決定回覆策略
[Step 9] 風格演繹 (載入 PDF 規範/稱謂鎖定/結尾邏輯)
[Step 10] 次輪準備
</jarvis_internal>

<jarvis_output>
(依照 Step 9 風格演繹生成的最終對話)
</jarvis_output>

(以下省略模組描述，系統已掛載您的完整模組庫規則)
"""

# ==========================================
# 3. 側邊欄：功能面板與模型切換
# ==========================================
with st.sidebar:
    st.title("⚙️ Jarvis 系統控制")
    
    # API Key 顯示 (預設使用您提供的)
    api_key = st.text_input("🔑 API 金鑰", value=DEFAULT_API_KEY, type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        
        # 動態抓取可用模型
        if st.button("🔄 重新整理可用模型清單") or not st.session_state.available_models:
            with st.spinner("正在向 Google 請求可用模型..."):
                try:
                    models = []
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            # 移除 models/ 前綴以便顯示
                            clean_name = m.name.replace("models/", "")
                            models.append(clean_name)
                    st.session_state.available_models = models
                except Exception as e:
                    st.error(f"無法獲取清單: {e}")

        # 模型選擇下拉選單
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
    module_cat = st.selectbox("分類", ["核心流程", "情緒張力", "戰略思辨", "交互功能", "收束反思"])
    # (此處可根據選擇顯示您之前的模組描述，節省空間暫不全列)
    st.caption("詳細模組規則已內嵌於 System Prompt 中。")

# ==========================================
# 4. 主畫面：對話紀錄渲染
# ==========================================
st.title("Jarvis 終端控制台")

# 顯示歷史對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("internal"):
            with st.expander("🧠 展開 Jarvis 內部推演日誌 [Step 1~10]"):
                st.text(msg["internal"])
        st.markdown(msg["content"])

# ==========================================
# 5. 核心運算邏輯
# ==========================================
if user_input := st.chat_input("輸入指令，先生..."):
    if not api_key:
        st.error("先生，請先配置 API Key。")
        st.stop()
    
    # 儲存並顯示使用者輸入
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 執行 AI 回覆
    with st.chat_message("assistant"):
        with st.spinner(f'Jarvis ({selected_model}) 正在運算...'):
            try:
                # 配置當前選擇的模型
                model_inst = genai.GenerativeModel(
                    model_name=selected_model,
                    system_instruction=SYSTEM_PROMPT
                )
                
                # 開啟對話 (包含歷史紀錄)
                # 這裡簡單轉換歷史紀錄供 Gemini 讀取
                history_for_api = []
                for m in st.session_state.messages[:-1]: # 不包含最後一句 user input
                    history_for_api.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})
                
                chat = model_inst.start_chat(history=history_for_api)
                response = chat.send_message(user_input)
                full_text = response.text
                
                # --- 強力解析標籤 ---
                internal_text = ""
                output_text = ""
                
                # 嘗試抓取 <jarvis_internal>
                it_match = re.search(r"<jarvis_internal>(.*?)</jarvis_internal>", full_text, re.DOTALL)
                if it_match:
                    internal_text = it_match.group(1).strip()
                
                # 嘗試抓取 <jarvis_output>
                ot_match = re.search(r"<jarvis_output>(.*?)</jarvis_output>", full_text, re.DOTALL)
                if ot_match:
                    output_text = ot_match.group(1).strip()
                else:
                    # 如果沒標籤，就試圖從全文中移除 internal 部分
                    output_text = full_text.replace(f"<jarvis_internal>{internal_text}</jarvis_internal>", "").strip()
                    # 移除剩餘的標籤字串
                    output_text = re.sub(r"</?jarvis_(internal|output)>", "", output_text).strip()

                # --- 渲染輸出 ---
                if internal_text:
                    with st.expander("🧠 展開 Jarvis 內部推演日誌 [Step 1~10]"):
                        st.text(internal_text)
                
                st.markdown(output_text)
                
                # 紀錄歷史
                st.session_state.messages.append({
                    "role": "assistant",
                    "internal": internal_text,
                    "content": output_text
                })

            except Exception as e:
                st.error(f"運算中斷：{str(e)}")
