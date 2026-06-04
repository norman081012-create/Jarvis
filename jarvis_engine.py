# ==========================================
# jarvis_engine.py
# ==========================================
import re
import google.generativeai as genai

def fetch_available_models(api_key):
    genai.configure(api_key=api_key)
    return [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

def extract_dashboard_data(internal_text):
    if not internal_text: return {}
    plain = internal_text.replace('**', '').replace('* ', '')

    def ext_line(pattern):
        m = re.search(pattern, plain, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "未解析到資料"

    # 完全對應新版 Step 1 ~ 10 變數
    return {
        "location": ext_line(r"位置[：:]\s*([^\n]*)"),
        "trend": ext_line(r"變化傾向[：:]\s*([^\n]*)"),
        "modules": ext_line(r"激活模組[：:]\s*([^\n]*)"),
        "tags": ext_line(r"本輪結算庫存[：:]\s*(.*?)(?=\n.*?\[Step 4\]|\Z)"),
        "intent": ext_line(r"產生策略[：:]\s*([^\n]*)"),
        "atmosphere": ext_line(r"氣氛[：:]\s*([^\n]*)"),
        "friendly": ext_line(r"友善度.*?[:：]\s*([^\n]*)"),
        "trust": ext_line(r"信任度.*?[:：]\s*([^\n]*)"),
        "sai": ext_line(r"SAI 社交優勢.*?[:：]\s*([^\n]*)"),
        "accuracy": ext_line(r"準確度.*?[:：]\s*([^\n]*)"),
        "bio_compute": ext_line(r"生物算力殘留值.*?[:：]\s*([^\n]*)"),
        "sai_strategy": ext_line(r"修正策略[：:]\s*([^\n]*)"),
        "matrix": ext_line(r"本輪設定級數[：:]\s*([^\n]*)"),
        "fusion": ext_line(r"融合決策[：:]\s*([^\n]*)"),
        "new_goal": ext_line(r"新目標 \(D\)[：:]\s*([^\n]*)"),
        "next_strategy": ext_line(r"決定次輪策略 \(D\)[：:]\s*([^\n]*)" )
    }

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text, audio_data=None):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    chat = model_inst.start_chat(history=history_for_api)
    
    if audio_data:
        response = chat.send_message([forced_template_text, audio_data])
    else:
        response = chat.send_message(forced_template_text)
        
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", response.text, flags=re.MULTILINE)
    
    # 精準切割 internal 與 output
    out_match = re.search(r"<jarvis_output>(.*?)</jarvis_output>", clean_text, flags=re.DOTALL | re.IGNORECASE)
    if out_match:
        output_text = out_match.group(1).strip()
        internal_text = clean_text[:out_match.start()]
    else:
        output_text = clean_text
        internal_text = clean_text
        
    internal_text = re.sub(r"</?jarvis_internal>", "", internal_text, flags=re.IGNORECASE).strip()
    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": response.text,
        "parsed_dash": extract_dashboard_data(internal_text)
    }
