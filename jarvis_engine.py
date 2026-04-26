# ==========================================
# jarvis_engine.py
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
    
    plain = internal_text.replace('**', '').replace('* ', '')

    def ext_line(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    def ext_multi(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    # 🔥 配合新版 Prompt 骨架，全面翻新 Regex 標籤
    data = {
        "modules": ext_line(r"激活模組[：:]\s*([^\n]*)"),
        
        # [Step 3] 從 24維度 改為 本輪結算庫存
        "tags": ext_multi(r"本輪結算庫存[：:]\s*(.*?)(?=\n.*?\[Step 4\]|\Z)"),
        
        "intent": ext_line(r"產生策略[：:]\s*([^\n]*)"),
        
        "friendly": ext_line(r"友善度 \(1~10\)[：:]\s*([^\n]*)"),
        "trust": ext_line(r"信任度 \(1~10\)[：:]\s*([^\n]*)"),
        "sai": ext_line(r"SAI 社交優勢 \(1~5\)[：:]\s*([^\n]*)"),
        "accuracy": ext_line(r"準確度 \(1~5\)[：:]\s*([^\n]*)"),
        
        # [Step 6] 移除(強制回歸均值 3)贅字
        "sai_strategy": ext_line(r"修正策略[：:]\s*([^\n]*)"),
        "sai_reason": ext_line(r"修正策略.*?判讀理由[：:]\s*([^\n]*)"),
        
        "matrix": ext_line(r"本輪設定級數[：:]\s*([^\n]*)"),
        # [Step 6] 連動矩陣文字微調
        "matrix_reason": ext_line(r"偽裝.*?判讀理由[：:]\s*([^\n]*)"),
        
        "strategy_b": ext_line(r"產生策略 B[：:]\s*([^\n]*)"),
        "fusion": ext_line(r"融合決策[：:]\s*([^\n]*)"),
        
        # [Step 10] 移除 / 目標庫存 贅字
        "new_goal": ext_line(r"新目標 \(D\)[：:]\s*([^\n]*)"),
        "next_strategy": ext_line(r"決定次輪策略 \(D\)[：:]\s*([^\n]*)")
    }
    return data

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    chat = model_inst.start_chat(history=history_for_api)
    response = chat.send_message(forced_template_text)
    full_text = response.text
    
    clean_text = re.sub(r"^```[a-z]*\n", "", full_text, flags=re.MULTILINE)
    clean_text = re.sub(r"\n```$", "", clean_text, flags=re.MULTILINE)
    
    internal_text = ""
    output_text = ""
    
    out_match = re.search(r"<jarvis_output>(.*)", clean_text, flags=re.DOTALL | re.IGNORECASE)
    
    if out_match:
        output_text = out_match.group(1)
        internal_text = clean_text[:out_match.start()]
    else:
        int_close_match = re.search(r"</jarvis_internal>(.*)", clean_text, flags=re.DOTALL | re.IGNORECASE)
        if int_close_match:
            output_text = int_close_match.group(1)
            internal_text = clean_text[:int_close_match.start()]
        else:
            output_text = clean_text
            internal_text = ""

    output_text = re.sub(r"</?jarvis_output>", "", output_text, flags=re.IGNORECASE).strip()
    internal_text = re.sub(r"</?jarvis_internal>", "", internal_text, flags=re.IGNORECASE).strip()

    parsed_dash = extract_dashboard_data(internal_text)

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": parsed_dash
    }
