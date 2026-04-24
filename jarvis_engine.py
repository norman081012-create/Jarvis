# jarvis_engine.py
import re
import google.generativeai as genai

def fetch_available_models(api_key):
    """向 Google 伺服器獲取可用的模型清單"""
    genai.configure(api_key=api_key)
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            clean_name = m.name.replace("models/", "")
            models.append(clean_name)
    return models

def process_jarvis_turn(api_key, selected_model, system_prompt, history_for_api, forced_template_text):
    """初始化模型、傳送訊息，並負責字串切割解析"""
    genai.configure(api_key=api_key)
    
    # 建立模型實體
    model_inst = genai.GenerativeModel(
        model_name=selected_model,
        system_instruction=system_prompt
    )
    
    # 啟動對話並傳送
    chat = model_inst.start_chat(history=history_for_api)
    response = chat.send_message(forced_template_text)
    full_text = response.text
    
    # --- 終極防呆切割邏輯 ---
    # 清理 markdown 區塊符號
    clean_text = re.sub(r"^```[a-z]*\n", "", full_text)
    clean_text = re.sub(r"\n```$", "", clean_text)
    
    internal_text = ""
    output_text = ""
    
    # 正規表示式抓取
    it_match = re.search(r"<\**jarvis_internal\**.*?>\s*(.*?)\s*</\**jarvis_internal\**.*?>", clean_text, re.DOTALL | re.IGNORECASE)
    ot_match = re.search(r"<\**jarvis_output\**.*?>\s*(.*?)\s*</\**jarvis_output\**.*?>", clean_text, re.DOTALL | re.IGNORECASE)

    if it_match:
        internal_text = it_match.group(1).strip()
    
    if ot_match:
        output_text = ot_match.group(1).strip()
    else:
        # 如果找不到 output 標籤，防呆處理
        if it_match:
            output_text = clean_text.replace(it_match.group(0), "").strip()
        else:
            output_text = clean_text

    return {
        "internal": internal_text,
        "output": output_text,
        "raw_full_text": full_text
    }
