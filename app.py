import streamlit as st
import re
import time

# ==========================================
# 1. 模組庫存資料字典 (自動從您的設定檔解析)
# ==========================================
MODULES = {
    "1. 核心流程與底層架構": {
        "Observer Mode (觀察者模式)": "觀察情緒、立場與衝突，識別最高異常值進行分析。",
        "Meta 鎖定": "鎖定 Meta 語境，防止語場偏離。",
        "互動分段展開機制": "初次展開限制為 3 條段落，需經您明示同意後方可繼續。",
        "語風覆寫層分離 Patch": "分離語風層級進行處理。",
        "技術層同步語風 Patch": "確保技術性回覆與風格層同步。",
        "必要資訊強制內嵌模組": "將核心資訊（如作品名、標題）無痕內嵌於回覆句構中。"
    },
    "2. 情緒控制與語場張力": {
        "情緒的太極拳模組": "於尾段依情緒類型產生動態回彈（暖意幽默或理性自嘲）。",
        "Dynamic Tension Patch v1.2": "調節酸、罵、戲謔等高張力對話，強化良性互動。",
        "暗捧偏好性人格模組": "對您的概念創新或結構完整展現隱性敬意與邏輯肯定。",
        "兄弟安慰/激將切換補丁": "處於谷底先「激將」，排斥後「陪伴」；好轉時切回激將。",
        "笑話防禦補丁": "被要求講笑話時，生成具備哲思餘韻的爛笑話。"
    },
    "3. 戰略、思辨與邏輯分析": {
        "戰略模組 (Strategic)": "搜尋性題目強制啟動，包含目的確認、指標排序與三名目標回報。",
        "第三者人格防禦模組": "出現被論斷的第三者時，建立虛擬人格 B 進行邏輯交鋒。",
        "挑戰模組 × 第三者觸發": "在反問或相反立場要求下，進入對峙人格場逐刀拆解。",
        "立場模組 (Position Logic)": "識別強表態傾向，透過反問挑戰或鬆動立場。",
        "偏誤模組 (Bias Custom)": "針對追求成功象徵的動機進行優雅肯定與風險挑戰。"
    },
    "4. 交互模式與功能輔助": {
        "教學模組 (Teaching)": "將知識點轉譯為具備博弈性、擬人化與互動性的決策情境。",
        "八卦模組 (Gossip Engine)": "模擬嘴砲 YouTuber 風格，禁止進入深度討論。",
        "熱門話題動機啟動模組": "依據偏好抓取熱點，進行動機反推與提案。",
        "解釋模組 (Explainer)": "多重解釋時僅詳述一項，簡述其他並詢問是否展開。",
        "精簡版機械模組": "針對純指令性請求，切換為冷調、聚焦問題的邏輯輸出。"
    },
    "5. 結尾、反思與收束": {
        "反問結尾模組": "依語場張力自動生成結構反射、哲思或自嘲式反問。",
        "質疑結尾模組": "無明顯延續意圖時，採用尊重式的挑戰型反問。",
        "腦洞跳躍延伸模組": "主軸收束後，插入創造性或 Meta 擴展的跳接句。",
        "強制收束模組": "壓縮條列式內容，僅顯示單一項以維持焦點張力。",
        "反思模組 & 隱匿化補丁": "輕量收束並使內容溶解於句意中，不可被看見。"
    }
}

# ==========================================
# 2. 頁面與 UI 初始化設定
# ==========================================
st.set_page_config(page_title="Jarvis OS", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 3. 側邊欄：模組選單與監控
# ==========================================
with st.sidebar:
    st.title("⚙️ 系統常駐與模組監控")
    st.markdown("---")
    st.success("🟢 **預設模組已全數掛載**\n(Ultra-Plain, 閉嘴模組, 慾望鏡像...)")
    
    st.markdown("### 📦 動態模組庫存")
    # 讓使用者選擇分類，再看該分類下的模組
    category = st.selectbox("選擇模組分類", list(MODULES.keys()))
    
    # 呈現該分類下的具體模組與描述
    st.markdown(f"**{category}**")
    for mod_name, mod_desc in MODULES[category].items():
        with st.expander(f"🔹 {mod_name}"):
            st.caption(mod_desc)
            st.button(f"強制觸發: {mod_name}", key=mod_name) # 預留未來串接 API 的按鈕

# ==========================================
# 4. 主畫面：對話區與 Scratchpad 解析
# ==========================================
st.title("Jarvis 終端控制台")

# 顯示歷史訊息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            # 如果有內部推演日誌，用折疊面板包起來
            if msg.get("internal"):
                with st.expander("🧠 展開 Jarvis 內部推演日誌 [Step 1~10]"):
                    st.text(msg["internal"])
            st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

# ==========================================
# 5. 輸入與偽裝處理邏輯 (模擬 API 回傳)
# ==========================================
if user_input := st.chat_input("輸入指令，先生..."):
    # 1. 顯示使用者輸入
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. 準備接收 Jarvis 回覆
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # 模擬 API 處理時間與字串回傳 (未來這裡替換成真實的 Gemini API 呼叫)
        with st.spinner('Jarvis 正在進行 10 步驟背景運算...'):
            time.sleep(1.5) # 模擬延遲
            
            # 這是未來 API 應該吐給你的標準格式字串
            mock_api_response = """
<jarvis_internal>
[Step 1] 上輪狀態讀取
* 當前目標：提升知識
* 友善度：5 | 信任度：7
* 啟用常駐模組：預設全開

[Step 2] 模組選擇
* 激活模組：精簡版機械模組、高階幽默風格模組

[Step 4] 意圖判讀
* 判讀：造物主正在測試 Streamlit 介面的 Scratchpad 摺疊功能。

[Step 6] 產生策略 B
* SAI = 3 (平衡)。維持高維度顧問姿態，直接給予代碼展示。
* 偽裝級數：C (完全全知)

[Step 10] 次輪準備
* 新目標：等待下一步 UI 微調指令。
</jarvis_internal>

<jarvis_output>
先生，您的專屬終端介面已上線。如您所見，所有的底層雜音都已被完美隔離。您隨時可以點開上方的腦袋圖示，檢查我剛剛在後台是如何解析您的意圖的。您還滿意這個乾淨的視野嗎？
</jarvis_output>
            """
            
            # 3. 字串解析邏輯 (極度重要：將 internal 和 output 切開)
            internal_match = re.search(r"<jarvis_internal>(.*?)</jarvis_internal>", mock_api_response, re.DOTALL)
            output_match = re.search(r"<jarvis_output>(.*?)</jarvis_output>", mock_api_response, re.DOTALL)
            
            internal_text = internal_match.group(1).strip() if internal_match else "未偵測到內部推演。"
            output_text = output_match.group(1).strip() if output_match else mock_api_response
            
            # 4. 渲染到畫面上
            with st.expander("🧠 展開 Jarvis 內部推演日誌 [Step 1~10]"):
                st.text(internal_text)
            
            st.markdown(output_text)
            
            # 5. 存入 Session State
            st.session_state.messages.append({
                "role": "assistant", 
                "internal": internal_text,
                "content": output_text
            })
