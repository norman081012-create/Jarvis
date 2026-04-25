# -----------------------------
# jarvis_config.py
# -----------------------------

# (將你提供的全新 SYSTEM_PROMPT 完整覆蓋原本的 SYSTEM_PROMPT，此處省略長文本以節省版面，請直接貼上你上文提供的 Prompt)

def get_forced_template(user_input, current_tags, current_user_mem, current_goals):
    """產生強制防偷懶的注入模板，並動態注入當前記憶庫存"""
    
    # 組合當前記憶狀態
    memory_injection = f"""
【當前系統庫存狀態 (請讀取並延續)】
* 標籤與特質庫存：{current_tags if current_tags else "無"}
* 使用者專屬記憶：{current_user_mem if current_user_mem else "無"}
* 目標庫存與策略：{current_goals if current_goals else "無"}
"""

    return f"""{user_input}

【系統底層最高優先級指令：禁止跳過推演】
你必須「直接複製」以下格式，並將內容填入。絕對不允許省略標籤或直接給出對話：

<jarvis_internal>
[Step 1] 庫存數據讀取{memory_injection}
[Step 2]
[Step 3]
[Step 4]
[Step 5]
[Step 6]
[Step 7]
[Step 8]
[Step 9]
[Step 10]
</jarvis_internal>
<jarvis_output>
(在這裡寫下最終回覆)
</jarvis_output>"""
