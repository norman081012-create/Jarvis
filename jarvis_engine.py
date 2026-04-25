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
    
    # 移除星號，讓正則比對不受 Markdown 粗體干擾
    plain = internal_text.replace('**', '').replace('* ', '')

    # 單行擷取：絕不跨行，保證分數不會抓到別的段落
    def ext_line(pattern):
        m = re.search(pattern, plain, re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    # 跨段落擷取：專門用來抓清單
    def ext_multi(pattern):
        m = re.search(pattern, plain, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    # 嚴格對齊你提供的原版骨架名稱
    data = {
        "modules": ext_line(r"激活模組.*?[:：]\s*([^\n]*)"),
        
        # 標籤庫存：從「本輪結算庫存」抓到下一個 [Step 4]
        "tags": ext_multi(r"本輪結算庫存.*?[:：]\s*(.*?)(?=\n.*\[Step 4\])"),
        # 新增記憶：從「動態處理」抓到「本輪結算庫存」
        "new_memory": ext_multi(r"動態處理.*?[:：]\s*(.*?)(?=\n.*本輪結算庫存)"),
        
        "intent": ext_line(r"產生策略.*?[:：]\s*([^\n]*)"),
        
        "friendly": ext_line(r"友善度 \(1~10\).*?[:：]\s*([^\n]*)"),
        "trust": ext_line(r"信任度 \(1~10\).*?[:：]\s*([^\n]*)"),
        "sai": ext_line(r"SAI 社交優勢 \(1~5\).*?[:：]\s*([^\n]*)"),
        "accuracy": ext_line(r"準確度 \(1~5\).*?[:：]\s*([^\n]*)"),
        
        "sai_strategy": ext_line(r"修正策略 \(強制回歸均值 3\).*?[:：]\s*([^\n]*)"),
        "sai_reason": ext_line(r"\[Step 6\].*?判讀理由.*?[:：]\s*([^\n]*)"),
        "matrix": ext_line(r"本輪設定級數.*?[:：]\s*([^\n]*)"),
        "matrix_reason": ext_line(r"連動矩陣.*?判讀理由.*?[:：]\s*([^\n]*)"),
        "strategy_b": ext_line(r"產生策略 B.*?[:：]\s*([^\n]*)"),
        
        "fusion": ext_line(r"融合決策.*?[:：]\s*([^\n]*)"),
        
        "new_goal": ext_line(r"新目標 \(D\) / 目標庫存.*?[:：]\s*([^\n]*)"),
        "next_strategy": ext_line(r"決定次輪策略 \(D\).*?[:：]\s*([^\n]*)")
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
