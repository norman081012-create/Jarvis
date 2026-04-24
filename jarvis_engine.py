# jarvis_engine.py
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
    
    def extract(pattern):
        match = re.search(pattern, plain_text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else "未解析到資料"

    data = {
        "modules": extract(r"激活模組.*?[:：]\s*(.*?)(?=\n.*\[Step|\n\n)"),
        "tags": extract(r"更新標籤.*?[:：]\s*(.*?)(?=\n.*\[Step|\n\n)"),
        "intent": extract(r"產生策略.*?[:：]\s*(.*?)(?=\n.*\[Step|\n\n)"),
        "friendly": extract(r"友善度.*?[:：]\s*(.*?)(?=\n)"),
        "trust": extract(r"信任度.*?[:：]\s*(.*?)(?=\n)"),
        "sai": extract(r"SAI 社交優勢.*?[:：]\s*(.*?)(?=\n)"),
        "accuracy": extract(r"準確度.*?[:：]\s*(.*?)(?=\n)"),
        "sai_strategy": extract(r"修正策略.*?[:：]\s*(.*?)(?=\n.*判讀理由)"),
        "sai_reason": extract(r"\[Step 6\].*?判讀理由.*?[:：]\s*(.*?)(?=\n.*全知全能)"),
        "matrix": extract(r"本輪設定級數.*?[:：]\s*(.*?)(?=\n)"),
        "matrix_reason": extract(r"矩陣.*?判讀理由.*?[:：]\s*(.*?)(?=\n.*產生策略 B)"),
        "strategy_b": extract(r"產生策略 B.*?[:：]\s*(.*?)(?=\n.*\[Step)"),
        "fusion": extract(r"融合決策.*?[:：]\s*(.*?)(?=\n.*\[Step)"),
        "new_goal": extract(r"新目標.*?[:：]\s*(.*?)(?=\n.*決定次輪)"),
        "next_strategy": extract(r"決定次輪策略.*?[:：]\s*(.*?)(?=$|</)")
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
    
    # 嘗試抓取標準標籤
    it_match = re.search(r"<\**jarvis_internal\**.*?>\s*(.*?)\s*</\**jarvis_internal\**.*?>", clean_text, re.DOTALL | re.IGNORECASE)
    ot_match = re.search(r"<\**jarvis_output\**.*?>\s*(.*?)\s*</\**jarvis_output\**.*?>", clean_text, re.DOTALL | re.IGNORECASE)

    if it_match:
        internal_text = it_match.group(1).strip()
    else:
        # 🔥 終極防呆：就算沒有標籤，只要看到 [Step 1] 到 [Step 10] 就強制挖出來
        fallback_match = re.search(r"(\[Step 1\].*?\[Step 10\].*?(?=\n\n|\Z|<))", clean_text, re.DOTALL | re.IGNORECASE)
        if fallback_match:
            internal_text = fallback_match.group(1).strip()
            
    if ot_match:
        output_text = ot_match.group(1).strip()
    else:
        # 拔除推演過程，剩下的就是純對話
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
