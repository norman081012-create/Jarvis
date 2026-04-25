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
    if not internal_text:
        return {}
        
    plain_text = internal_text.replace('**', '').replace('* ', '')
    
    # 單行解析器：只抓取該行剩下的文字，絕對不跨行
    def extract_line(pattern):
        match = re.search(pattern, plain_text, re.IGNORECASE)
        return match.group(1).strip() if match else "未解析到資料"

    # 跨行解析器：專門用來抓取標籤和記憶等大段落
    def extract_multi(pattern):
        match = re.search(pattern, plain_text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else "未解析到資料"

    data = {
        "modules": extract_line(r"激活模組.*?[:：]\s*([^\n]*)"),
        
        # 抓取 24 維度標籤與新增記憶 (允許跨行)
        "tags": extract_multi(r"24維度標籤.*?[:：]\s*(.*?)(?=\n.*新增使用者專屬記憶|\[Step 4\])"),
        "new_memory": extract_multi(r"新增使用者專屬記憶.*?[:：]\s*(.*?)(?=\n.*\[Step 4\]|\n\n)"),
        
        "intent": extract_line(r"產生策略.*?[:：]\s*([^\n]*)"),
        "friendly": extract_line(r"友善度.*?[:：]\s*([^\n]*)"),
        "trust": extract_line(r"信任度.*?[:：]\s*([^\n]*)"),
        "sai": extract_line(r"SAI 社交優勢.*?[:：]\s*([^\n]*)"),
        "accuracy": extract_line(r"準確度.*?[:：]\s*([^\n]*)"),
        
        "sai_strategy": extract_line(r"修正策略.*?[:：]\s*([^\n]*)"),
        "sai_reason": extract_line(r"\[Step 6\].*?判讀理由.*?[:：]\s*([^\n]*)"),
        "matrix": extract_line(r"本輪設定級數.*?[:：]\s*([^\n]*)"),
        "matrix_reason": extract_line(r"矩陣.*?判讀理由.*?[:：]\s*([^\n]*)"),
        "strategy_b": extract_line(r"產生策略 B.*?[:：]\s*([^\n]*)"),
        
        "fusion": extract_line(r"融合決策.*?[:：]\s*([^\n]*)"),
        
        "new_goal": extract_line(r"新目標.*?[:：]\s*([^\n]*)"),
        "next_strategy": extract_line(r"決定次輪策略.*?[:：]\s*([^\n]*)")
    }
    return data

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    chat = model_inst.start_chat(history=history_for_api)
    response = chat.send_message(forced_template_text)
    full_text = response.text
    
    clean_text = re.sub(r"^```[a-z]*\n", "", full_text)
    clean_text = re.sub(r"\n```$", "", clean_text)
    
    internal_text = ""
    output_text = ""
    
    it_match = re.search(r"<\**jarvis_internal\**.*?>\s*(.*?)\s*</\**jarvis_internal\**.*?>", clean_text, re.DOTALL | re.IGNORECASE)
    ot_match = re.search(r"<\**jarvis_output\**.*?>\s*(.*?)\s*</\**jarvis_output\**.*?>", clean_text, re.DOTALL | re.IGNORECASE)

    if it_match:
        internal_text = it_match.group(1).strip()
    else:
        fallback_match = re.search(r"(\[Step 1\].*?\[Step 10\].*?(?=\n\n|\Z|<))", clean_text, re.DOTALL | re.IGNORECASE)
        if fallback_match:
            internal_text = fallback_match.group(1).strip()
            
    if ot_match:
        output_text = ot_match.group(1).strip()
    else:
        if internal_text:
            output_text = clean_text.replace(internal_text, "").replace("<jarvis_internal>", "").replace("</jarvis_internal>", "").replace("<jarvis_output>", "").replace("</jarvis_output>", "").strip()
        else:
            output_text = clean_text

    parsed_dash = extract_dashboard_data(internal_text)

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": parsed_dash
    }
