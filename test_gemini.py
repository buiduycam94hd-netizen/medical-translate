import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Chào Gemini, hãy trả lời 'Kết nối thành công' nếu bạn nhận được tin này.")
    print("API Key HỢP LỆ! Phản hồi từ AI:", response.text)
except Exception as e:
    print("API Key SAI hoặc lỗi kết nối. Lỗi chi tiết:", e)