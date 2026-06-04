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

    # 針對 Jarvis 2.0 心理狀態的 Regex 提取
    data = {
        "overload": ext_line(r"情緒負荷判定.*?[:：]\s*([^\n]*)"),
        "defense": ext_line(r"防衛機制觸發計數.*?[:：]\s*([^\n]*)"),
        "modules": ext_line(r"激活模組[：:]\s*([^\n]*)"),
        "tags": ext_line(r"本輪結算庫存[：:]\s*(.*?)(?=\n.*?\[Step 4\]|\Z)"),
        "intent": ext_line(r"產生策略[：:]\s*([^\n]*)"),
        
        "atmosphere": ext_line(r"氣氛[：:]\s*([^\n]*)"),
        "empathy": ext_line(r"共情度.*?[:：]\s*([^\n]*)"),
        "trust": ext_line(r"信任度.*?[:：]\s*([^\n]*)"),
        "sai_pose": ext_line(r"SAI 陪伴姿態.*?[:：]\s*([^\n]*)"),
        "emotional_compute": ext_line(r"情感算力殘留值.*?[:：]\s*([^\n]*)"),
        
        "strategy_b": ext_line(r"產生策略 B[：:]\s*([^\n]*)"),
        "fusion": ext_line(r"融合決策[：:]\s*([^\n]*)"),
        "new_goal": ext_line(r"新目標 \(D\)[：:]\s*([^\n]*)"),
        "next_strategy": ext_line(r"決定次輪策略 \(D\)[：:]\s*([^\n]*)")
    }
    return data

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text, audio_data=None):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    
    chat = model_inst.start_chat(history=history_for_api)
    
    # 支援多模態：若有音訊，將音訊與指令一起送出
    if audio_data:
        response = chat.send_message([forced_template_text, audio_data])
    else:
        response = chat.send_message(forced_template_text)
        
    full_text = response.text
    
    # 清理與分割邏輯
    clean_text = re.sub(r"^```[a-z]*\n", "", full_text, flags=re.MULTILINE)
    clean_text = re.sub(r"\n```$", "", clean_text, flags=re.MULTILINE)
    
    internal_text, output_text = "", ""
    out_match = re.search(r"<jarvis_output>(.*?)</jarvis_output>", clean_text, flags=re.DOTALL | re.IGNORECASE)
    
    if out_match:
        output_text = out_match.group(1).strip()
        internal_text = clean_text[:out_match.start()]
    else:
        output_text = clean_text
    
    internal_text = re.sub(r"</?jarvis_internal>", "", internal_text, flags=re.IGNORECASE).strip()
    parsed_dash = extract_dashboard_data(internal_text)

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": parsed_dash
    }
