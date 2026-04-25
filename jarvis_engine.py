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
            models.append(m.name.replace("models/", ""))
    return models

def extract_dashboard_data(internal_text):
    if not internal_text: return {}
    plain = internal_text.replace('**', '')
    
    def ext(pattern, group=1):
        m = re.search(pattern, plain, re.DOTALL | re.IGNORECASE)
        return m.group(group).strip() if m else "未解析到資料"

    # 精準對應新版乾淨骨架
    data = {
        "tags_inventory": ext(r"本輪結算庫存.*?(\【A\.\s*職場能力\】.*?(?=新增使用者專屬記憶|\[Step 4\]|\Z))"),
        "user_memory_delta": ext(r"新增使用者專屬記憶[：:]\s*(.*?)(?=\[Step 4\]|\n\n|\Z)"),
        "goal_inventory": ext(r"新目標.*?目標庫存[：:]\s*(.*?)(?=\n.*決定次輪策略|\Z)"),
        
        "modules": ext(r"激活模組[：:]\s*(.*?)(?=\n.*\[Step|\n\n|\Z)"),
        "intent": ext(r"產生策略 A[：:]\s*(.*?)(?=\n.*\[Step|\n\n|\Z)"),
        "friendly": ext(r"友善度[：:]\s*(.*?)(?=\n|\Z)"),
        "trust": ext(r"信任度[：:]\s*(.*?)(?=\n|\Z)"),
        "sai": ext(r"SAI 社交優勢[：:]\s*(.*?)(?=\n|\Z)"),
        "accuracy": ext(r"準確度[：:]\s*(.*?)(?=\n|\Z)"),
        "sai_strategy": ext(r"SAI 修正策略[：:]\s*(.*?)(?=\n.*本輪設定|\[)"),
        "matrix": ext(r"本輪設定級數.*?[：:]\s*(.*?)(?=\n.*產生策略 B)"),
        "strategy_b": ext(r"產生策略 B[：:]\s*(.*?)(?=\n.*\[Step|\Z)"),
        "fusion": ext(r"融合決策[：:]\s*(.*?)(?=\n.*\[Step|\Z)"),
        "next_strategy": ext(r"決定次輪策略.*?[：:]\s*(.*?)(?=$|</|\Z)")
    }
    return data

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    genai.configure(api_key=api_key)
    model_inst = genai.GenerativeModel(model_name=selected_model, system_instruction=system_prompt)
    chat = model_inst.start_chat(history=history_for_api)
    response = chat.send_message(forced_template_text)
    full_text = response.text
    
    clean_text = re.sub(r"^```[a-z]*\n|\n```$", "", full_text, flags=re.MULTILINE)
    
    it_match = re.search(r"<jarvis_internal>(.*?)</jarvis_internal>", clean_text, re.DOTALL | re.IGNORECASE)
    internal_text = it_match.group(1).strip() if it_match else ""
    
    out_match = re.search(r"<jarvis_output>(.*)</jarvis_output>", clean_text, re.DOTALL | re.IGNORECASE)
    if out_match:
        output_text = out_match.group(1).strip()
    else:
        output_text = clean_text.replace(f"<jarvis_internal>{internal_text}</jarvis_internal>", "").strip()

    output_text = re.sub(r"</?jarvis_output>|</?jarvis_internal>", "", output_text, flags=re.IGNORECASE).strip()

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text,
        "parsed_dash": extract_dashboard_data(internal_text)
    }
