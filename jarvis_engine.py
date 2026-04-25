# ==========================================
# jarvis_engine.py
# 核心邏輯、API 通訊與正則解析引擎
# ==========================================
import re
import google.generativeai as genai

def fetch_available_models(api_key):
    genai.configure(api_key=api_key)
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            clean_name = m.name.replace("models/", "")
            models.append(clean_name)
    return models

def extract_dashboard_data(internal_text):
    if not internal_text: return {}
    
    # 移除星號，讓正則比對不受 Markdown 粗體干擾
    plain = internal_text.replace('**', '').replace('* ', '')

    # 單行擷取：絕不跨行，保證分數不會抓到別的段落
    def ext_line(pattern):
        # 加上 DOTALL 讓 .*? 允許尋找錨點，但 ([^\n]*) 保證最終只抓單行結果
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    # 跨段落擷取：專門用來抓清單
    def ext_multi(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    data = {
        "modules": ext_line(r"激活模組[：:]\s*([^\n]*)"),
        "tags": ext_multi(r"24維度標籤[：:]\s*(.*?)(?=\n.*?新增使用者專屬記憶|\[Step 4\]|\Z)"),
        "new_memory": ext_multi(r"新增使用者專屬記憶[：:]\s*(.*?)(?=\n.*?\[Step 4\]|\Z)"),
        "intent": ext_line(r"產生策略[：:]\s*([^\n]*)"),
        "friendly": ext_line(r"友善度 \(1~10\)[：:]\s*([^\n]*)"),
        "trust": ext_line(r"信任度 \(1~10\)[：:]\s*([^\n]*)"),
        "sai": ext_line(r"SAI 社交優勢 \(1~5\)[：:]\s*([^\n]*)"),
        "accuracy": ext_line(r"準確度 \(1~5\)[：:]\s*([^\n]*)"),
        "sai_strategy": ext_line(r"修正策略 \(強制回歸均值 3\)[：:]\s*([^\n]*)"),
        "sai_reason": ext_line(r"修正策略.*?判讀理由[：:]\s*([^\n]*)"),
        "matrix": ext_line(r"本輪設定級數[：:]\s*([^\n]*)"),
        "matrix_reason": ext_line(r"連動矩陣.*?判讀理由[：:]\s*([^\n]*)"),
        "strategy_b": ext_line(r"產生策略 B[：:]\s*([^\n]*)"),
        "fusion": ext_line(r"融合決策[：:]\s*([^\n]*)"),
        "new_goal": ext_line(r"新目標 \(D\) / 目標庫存[：:]\s*([^\n]*)"),
        "next_strategy": ext_line(r"決定次輪策略 \(D\)[：:]\s*([^\n]*)")
    }
    return data

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    chat = model_inst.start_chat(history=history_for_api)
    response = chat.send_message(forced_template_text)
    full_text = response.text
    
    # 清理最外層可能夾帶的 markdown 區塊符號
    clean_text = re.sub(r"^```[a-z]*\n", "", full_text, flags=re.MULTILINE)
    clean_text = re.sub(r"\n```$", "", clean_text, flags=re.MULTILINE)
    
    internal_text = ""
    output_text = ""
    
    # ==========================================
    # 🔪 終極暴力切割法：直接用錨點切斷字串
    # ==========================================
    # 1. 尋找 <jarvis_output> 作為分水嶺
    out_match = re.search(r"<jarvis_output>(.*)", clean_text, flags=re.DOTALL | re.IGNORECASE)
    
    if out_match:
        output_text = out_match.group(1)
        internal_text = clean_text[:out_match.start()]
    else:
        # 2. 如果連 <jarvis_output> 都忘了寫，尋找 </jarvis_internal> 切割
        int_close_match = re.search(r"</jarvis_internal>(.*)", clean_text, flags=re.DOTALL | re.IGNORECASE)
        if int_close_match:
            output_text = int_close_match.group(1)
            internal_text = clean_text[:int_close_match.start()]
        else:
            # 3. 雙重失敗，整包丟給輸出
            output_text = clean_text
            internal_text = ""

    # 拔除內文殘留的系統標籤，確保畫面乾淨
    output_text = re.sub(r"</?jarvis_output>", "", output_text, flags=re.IGNORECASE).strip()
    internal_text = re.sub(r"</?jarvis_internal>", "", internal_text, flags=re.IGNORECASE).strip()

    # 進行資料擷取
    parsed_dash = extract_dashboard_data(internal_text)

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": parsed_dash
    }
