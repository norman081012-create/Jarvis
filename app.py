import streamlit as st
import avatar_config as cfg
import avatar_engine as engine
import avatar_presets as presets
import re
from gtts import gTTS
import io

# ==========================================
# 語音播放模組 (gTTS 記憶體串流)
# ==========================================
def play_avatar_voice(text):
    # 清理文字：移除括號內的動作描述 (例如 "(嘆氣)", "（轉頭）")，避免語音引擎朗讀
    clean_text = re.sub(r'\(.*?\)|（.*?）', '', text).strip()
    
    if not clean_text:
        return
        
    try:
        tts = gTTS(text=clean_text, lang='zh-tw')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_bytes = audio_buffer.getvalue()
        
        # 渲染不可見的播放器並強制自動播放
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"語音模組錯誤: {str(e)}")

# ==========================================
# 1. 狀態與路由初始化
# ==========================================
st.set_page_config(page_title="Project AVATAR 認知終端", layout="wide", initial_sidebar_state="expanded")

if "current_page" not in st.session_state:
    st.session_state.current_page = "manager"
if "avatars" not in st.session_state:
    st.session_state.avatars = {}
if "active_avatar_name" not in st.session_state:
    st.session_state.active_avatar_name = None
if "available_models" not in st.session_state:
    st.session_state.available_models = []
    
if "temp_seeds" not in st.session_state:
    st.session_state.temp_seeds = []

# ==========================================
# 工具函式：繪製客製化生命條 (Health Bar)
# ==========================================
def render_health_bar(val_str, title, min_val, max_val, color):
    try:
        num = float(re.search(r'-?\d+\.?\d*', val_str).group())
    except:
        num = min_val
        
    clamped_num = max(min_val, min(num, max_val))
    pct = (clamped_num - min_val) / (max_val - min_val) * 100

    html = f"""
    <div style="margin-bottom: 18px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <strong style="font-size: 14px;">{title}</strong>
            <span style="color: {color}; font-weight: bold; font-size: 16px;">{num}</span>
        </div>
        <div style="width: 100%; background-color: #2b2b2b; border-radius: 8px; height: 16px; border: 1px solid #444;">
            <div style="width: {pct}%; background-color: {color}; height: 100%; border-radius: 7px; transition: width 0.5s ease-in-out;"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ==========================================
# 2. 側邊欄：全局設定
# ==========================================
with st.sidebar:
    st.title("⚙️ AVATAR 系統控制")
    api_key = st.text_input("🔑 API 金鑰", value=cfg.DEFAULT_API_KEY, type="password")
    
    selected_model = None
    if api_key:
        if st.button("🔄 獲取模型清單") or not st.session_state.available_models:
            with st.spinner("請求中..."):
                try:
                    st.session_state.available_models = engine.fetch_available_models(api_key)
                except Exception as e:
                    st.error(f"錯誤: {e}")

        if st.session_state.available_models:
            default_idx = next((i for i, m in enumerate(st.session_state.available_models) if "pro-preview" in m or "3.1-pro" in m), 0)
            selected_model = st.selectbox("🤖 運算核心", st.session_state.available_models, index=default_idx)

            if st.session_state.current_page == "simulation" and st.session_state.active_avatar_name:
                avatar_name = st.session_state.active_avatar_name
                if avatar_name in st.session_state.avatars:
                    avatar_data = st.session_state.avatars[avatar_name]
                    latest_msg = next((msg for msg in reversed(avatar_data["messages"]) if msg["role"] == "assistant"), None)
                    
                    if latest_msg:
                        st.divider()
                        st.caption("⚙️ 開發者底層監控 (Raw Data)")
                        st.code(latest_msg.get("raw_text", "無資料"), language="markdown")

# ==========================================
# 3. 頁面 1：人物建檔與管理庫
# ==========================================
def render_manager_page():
    st.title("🌌 Project AVATAR - 人格容器庫")
    st.markdown("在此建立新的意識容器，或載入內建人格進行深度模擬。")
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("➕ 建立新容器 (New Avatar)")
        
        a_name = st.text_input("人物代號 (Name)*", placeholder="例如：Alex")
        col_a, col_g = st.columns(2)
        with col_a:
            a_age = st.number_input("年齡", min_value=1, max_value=120, value=33)
        with col_g:
            a_gender = st.selectbox("性別", ["男性", "女性", "非二元", "保密"])
            
        st.divider()
        
        st.markdown("##### 🌱 注入靈魂種子 (特質/設定)")
        col_seed_in, col_seed_btn = st.columns([7, 3])
        with col_seed_in:
            new_seed = st.text_input("輸入單一特質", placeholder="例如：個性機車", key="seed_input_box", label_visibility="collapsed")
        with col_seed_btn:
            if st.button("➕ 加入種子", use_container_width=True):
                if new_seed and new_seed not in st.session_state.temp_seeds:
                    st.session_state.temp_seeds.append(new_seed)
                    st.rerun()
                    
        if st.session_state.temp_seeds:
            st.write("**已加入的種子：**")
            for i, seed in enumerate(st.session_state.temp_seeds):
                sc1, sc2 = st.columns([8, 2])
                sc1.info(f"🏷️ {seed}")
                if sc2.button("❌ 刪除", key=f"del_seed_{i}", use_container_width=True):
                    st.session_state.temp_seeds.pop(i)
                    st.rerun()
            st.divider()
            core_seed_label = st.selectbox("⭐ 選定核心種子 (僅供 UI 標示)", st.session_state.temp_seeds)
        else:
            st.caption("尚未加入任何特質種子。")
            core_seed_label = "未設定"
            
        st.divider()

        if st.button("🚀 注入靈魂並生成矩陣", type="primary", use_container_width=True):
            if not api_key or not selected_model:
                st.error("請先在側邊欄設定 API Key 與模型。")
            elif not a_name:
                st.error("請填寫人物代號！")
            elif a_name in st.session_state.avatars:
                st.error("此代號已存在，請換一個名字。")
            else:
                first_seed = f"{a_age}歲{a_gender}"
                all_seeds = [first_seed] + st.session_state.temp_seeds
                
                with st.spinner("正在編譯核心模塊矩陣 (這可能需要幾十秒)..."):
                    try:
                        generated_matrix = engine.generate_avatar_matrix(api_key, selected_model, all_seeds)
                        st.session_state.avatars[a_name] = {
                            "name": a_name,
                            "first_seed": first_seed,
                            "core_seed_label": core_seed_label,
                            "seeds": list(st.session_state.temp_seeds),
                            "matrix": generated_matrix,
                            "messages": [], 
                            "scene": "我們現在正在進行一場普通的初次見面談話。",
                            "user_perception": "一位剛認識的普通陌生人。",
                            "core_target": "維持基本社交禮儀，完成這次對話。(強度：低)"
                        }
                        st.session_state.temp_seeds = []
                        st.success(f"✅ {a_name} 意識容器建立完成！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"矩陣生成失敗: {str(e)}")

    with col2:
        st.subheader("📂 已存檔與內建容器")
        
        if st.button("✨ 載入內建範例人格：唐銘駿", use_container_width=True):
            if "唐銘駿" not in st.session_state.avatars:
                st.session_state.avatars["唐銘駿"] = presets.PRESETS["唐銘駿"]
                st.success("唐銘駿已載入資料庫！")
                st.rerun()
            else:
                st.info("唐銘駿已經在資料庫中了。")
                
        st.divider()

        if not st.session_state.avatars:
            st.info("目前沒有任何人物檔案。請在左側建立或載入內建人格。")
        else:
            for name, data in st.session_state.avatars.items():
                with st.expander(f"👤 {name} ({data['first_seed']} / 核心: {data.get('core_seed_label', '無')})", expanded=True):
                    st.caption(f"附加種子: {', '.join(data['seeds']) if data['seeds'] else '無'}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button(f"▶️ 進入模擬", key=f"sim_{name}", type="primary"):
                            st.session_state.active_avatar_name = name
                            st.session_state.current_page = "simulation"
                            st.rerun()
                    with col_btn2:
                        with st.popover("🔍 查看靈魂矩陣"):
                            st.code(data['matrix'], language="markdown")

# ==========================================
# 4. 頁面 2：核心認知終端 (Simulation Page)
# ==========================================
def render_simulation_page():
    avatar_name = st.session_state.active_avatar_name
    avatar_data = st.session_state.avatars[avatar_name]
    core_label = avatar_data.get('core_seed_label', '未設定')
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 8, 1])
    with col_nav1:
        if st.button("⬅️ 返回人物庫"):
            st.session_state.current_page = "manager"
            st.rerun()
    with col_nav2:
        st.markdown(f"### 🧠 測試對象：**{avatar_name}** | {avatar_data['first_seed']} / 核心: {core_label}")
    with col_nav3:
        if st.button("🔄 刷新對話", type="primary"):
            st.session_state.avatars[avatar_name]["messages"] = []
            st.rerun()

    with st.expander("⚙️ 動態環境、視角與動機設定 (可隨時修改，下回合生效)", expanded=True):
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            new_scene = st.text_area("🎬 當下場景與客觀前提", value=avatar_data['scene'], height=80)
        with col_s2:
            new_perception = st.text_area("👁️ Avatar 眼中的你", value=avatar_data.get('user_perception', ''), height=80)
        with col_s3:
            new_target = st.text_area("🎯 Avatar 核心目標與強度", value=avatar_data.get('core_target', ''), height=80)
            
        if new_scene != avatar_data['scene']: st.session_state.avatars[avatar_name]['scene'] = new_scene
        if new_perception != avatar_data.get('user_perception'): st.session_state.avatars[avatar_name]['user_perception'] = new_perception
        if new_target != avatar_data.get('core_target'): st.session_state.avatars[avatar_name]['core_target'] = new_target

    st.divider()

    latest_msg = None
    if avatar_data["messages"]:
        for msg in reversed(avatar_data["messages"]):
            if msg["role"] == "assistant":
                latest_msg = msg
                break
                
    if latest_msg and latest_msg.get("parsed_dash"):
        d = latest_msg["parsed_dash"]
        
        mf_full = d.get('mf', '20')
        mf_val = mf_full.split('(')[0].strip()
        mf_reason = mf_full[len(mf_val):].strip()
        st.markdown(f"**🎭 面具疲勞度 (MF): {mf_val} / 100** {mf_reason}")
        
        ai_scan = d.get("ai_scan", "0")
        if ai_scan != "0" and ai_scan != "No Data":
            st.error(f"🛡️ 圖靈測試防禦機制啟動：⚠️ 偵測到 AI 塑膠味！入侵值: {ai_scan}")
            
        col_bars, col_details = st.columns([1, 1], gap="large")
        
        with col_bars:
            st.markdown("##### 🧬 核心心理指標")
            render_health_bar(d.get("l_val", "0"), "L (好感度)", -10, 20, "#00cc96")   
            render_health_bar(d.get("sai", "50"), "SAI (地位感知)", 0, 100, "#ab63fa") 
            render_health_bar(d.get("t_val", "0"), "T (信任度)", -10, 20, "#636efa")   
            render_health_bar(d.get("bd", "100"), "B-D (邊界防禦)", 0, 100, "#ef553b") 

        with col_details:
            st.markdown("##### 🔍 詳細心理推演")
            
            d_r1c1, d_r1c2 = st.columns(2)
            with d_r1c1:
                st.markdown("**🧠 戰略判斷**")
                st.info(d.get("mod_b", "無資料"))
            with d_r1c2:
                st.markdown("**🌋 真實內在反射**")
                st.warning(d.get("mod_c", "無資料"))
                
            d_r2c1, d_r2c2 = st.columns(2)
            with d_r2c1:
                st.markdown("**🎭 職業面具偽裝**")
                st.success(d.get("mod_d", "無資料"))
            with d_r2c2:
                st.markdown("**🎯 次輪準備**")
                st.write(d.get("mod_a", "無資料"))
    else:
        st.caption("等待首輪對話產生 VFO 數據...")

    st.divider()
    
    # 渲染對話歷史
    for msg in avatar_data['messages']:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    if user_input := st.chat_input(f"對 {avatar_name} 說點什麼..."):
        if not api_key:
            st.error("請先配置 API Key。")
            st.stop()
            
        st.session_state.avatars[avatar_name]["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner(f'{avatar_name} 運算中...'):
                try:
                    history_for_api = []
                    for m in avatar_data["messages"][:-1]:
                        if m["role"] == "user":
                            history_for_api.append({"role": "user", "parts": [m["content"]]})
                        else:
                            full_memory = m.get("raw_text", m["content"])
                            history_for_api.append({"role": "model", "parts": [full_memory]})
                            
                    forced_input = cfg.get_forced_template(user_input)
                    
                    dynamic_system_prompt = (
                        avatar_data['matrix'] + "\n\n" + 
                        cfg.BASE_SYSTEM_RULES + 
                        f"\n\n【System Absolute Override - 當前動態環境與狀態】\n"
                        f"🎬 1. 互動場景與前提：\n{avatar_data['scene']}\n\n"
                        f"👁️ 2. {avatar_name} 眼中的使用者狀態 (外貌/身分/客觀評估)：\n{avatar_data['user_perception']}\n\n"
                        f"🎯 3. {avatar_name} 當下的核心目標 (Core Target) 與驅動強度：\n{avatar_data['core_target']}\n"
                        f"(⚠️ VFO 引擎指令：請將上述 Target 強制寫入並覆蓋初始 Core Target，且在 Step 1 戰略判斷中，必須嚴格受此 Target 強度與使用者狀態所驅動。)"
                    )
                    
                    result = engine.process_avatar_turn(
                        api_key=api_key,
                        selected_model=selected_model,
                        system_prompt=dynamic_system_prompt,
                        history_for_api=history_for_api,
                        forced_template_text=forced_input
                    )
                    
                    # 1. 渲染文字回覆
                    st.markdown(result["output"])
                    
                    # 2. 強制觸發語音播放 (過濾動作標籤)
                    play_avatar_voice(result["output"])
                    
                    # 3. 儲存至 Session State
                    st.session_state.avatars[avatar_name]["messages"].append({
                        "role": "assistant",
                        "raw_text": result["raw_full_text"],     
                        "content": result["output"],
                        "parsed_dash": result["parsed_dash"]
                    })
                    
                    st.rerun() 

                except Exception as e:
                    st.error(f"運算中斷：{str(e)}")

# ==========================================
# 5. 主程式路由執行
# ==========================================
if st.session_state.current_page == "manager":
    render_manager_page()
elif st.session_state.current_page == "simulation":
    if st.session_state.active_avatar_name:
        render_simulation_page()
    else:
        st.session_state.current_page = "manager"
        st.rerun()
