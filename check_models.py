import os
from google import genai
from dotenv import load_dotenv

# Tải API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

print("Đang kết nối để lấy danh sách Model...")
try:
    client = genai.Client(api_key=API_KEY)
    
    print("\n=== DANH SÁCH MODEL BẠN CÓ THỂ DÙNG ===")
    # Lấy danh sách các model khả dụng
    for model in client.models.list():
        # Lọc ra những model hỗ trợ chức năng tạo văn bản (generateContent)
        if "generateContent" in getattr(model, 'supported_actions', []):
            print(f"- {model.name}")
            
    print("=======================================")
except Exception as e:
    print(f"Lỗi khi lấy danh sách: {e}")