import 
import tempfile
from gtts import gTTS

# --- 系統設定與提示詞常數 ---
JARVIS_SYSTEM_PROMPT = """
你現在是 Jarvis。請嚴格遵守以下運作邏輯：
1. 在背景執行 <jarvis_internal> 的 Step 1 到 Step 10 思考過程，但不要顯示出來。
2. 最終回覆必須包裝在 <jarvis_output> 標籤中。
3. 語氣維持精煉、帶有輕度工程師語感，稱呼使用者為「先生」。
4. 針對使用者的輸入，給予最直接、邏輯清晰的解答。
"""

def generate_llm_response(user_input):
    """
    此函數負責處理邏輯。
    在實際應用中，您應將此處替換為呼叫 OpenAI, Gemini 或 Claude 的 API 程式碼，
    並將 JARVIS_SYSTEM_PROMPT 傳入作為 System Message。
    """
    # [模擬 API 回傳結果] - 這裡暫時以字串格式化模擬 LLM 回覆
    # 實際串接時，請擷取 LLM 回傳的 <jarvis_output> 內容
    mock_response = f"先生，已收到您的指令：「{user_input}」。系統底層模組已更新，並以 100.00% 的完成度轉譯為語音輸出。"
    return mock_response

def speak(text, lang='zh-tw'):
    """
    將純文字轉換為語音並播放
    """
    try:
        # print(" [系統提示] 語音生成中...")
        tts = gTTS(text=text, lang=lang)
        
        # 建立暫存音檔
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_filename = fp.name
            
        tts.save(temp_filename)
        
        # 跨平台播放音檔
        if os.name == 'nt':  # Windows
            # 使用 start 會開啟預設播放器，若要背景播放可考慮安裝 playsound 庫
            os.system(f"start {temp_filename}")
        elif os.uname().sysname == 'Darwin':  # macOS
            os.system(f"afplay {temp_filename}")
        else:  # Linux
            os.system(f"mpg123 {temp_filename}") # 請確保系統有安裝 mpg123 或使用其他播放器如 aplay
            
    except Exception as e:
        print(f"\n[Error] 語音模組發生錯誤: {e}")

def main():
    print("="*50)
    print(" Jarvis 核心系統初始化中... [gTTS 模組已掛載]")
    print("="*50)
    
    while True:
        try:
            user_input = input("\n[User Input] 請輸入指令 (或輸入 'exit' 關閉系統): ")
            
            if user_input.strip().lower() in ['exit', 'quit']:
                closing_words = "先生，系統正在進入休眠模式。隨時等候您的差遣。"
                print(f"\n<jarvis_output>\n{closing_words}\n</jarvis_output>")
                speak(closing_words)
                break
                
            if not user_input.strip():
                continue

            # 1. 將輸入傳遞給邏輯處理中心 (此處模擬 LLM 處理)
            response_text = generate_llm_response(user_input)
            
            # 2. 終端機文字輸出
            print(f"\n<jarvis_output>\n{response_text}\n</jarvis_output>")
            
            # 3. 語音輸出 (只唸出輸出文字，過濾掉 XML 標籤)
            speak(response_text)
            
        except KeyboardInterrupt:
            print("\n[系統提示] 偵測到強制中斷指令，系統強制關閉。")
            break

if __name__ == "__main__":
    main()
