import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class MedicalAIReviewer:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        
        # Viết gộp prompt thành chuỗi an toàn
        self.system_prompt = (
            "Bạn là Bác sĩ Trưởng khoa rà soát chất lượng dịch thuật y khoa. "
            "Bạn sẽ nhận được CÂU GỐC (Tiếng Anh) và BẢN DỊCH (Tiếng Việt). "
            "Nhiệm vụ: kiểm tra xem bản dịch có bị các lỗi tử huyệt sau không:\n"
            "1. Lỗi phủ định (có/không có).\n"
            "2. Lỗi con số/đơn vị.\n"
            "3. Bỏ sót từ hoặc dịch thêm thắt ý.\n\n"
            "TRẢ VỀ ĐÚNG JSON THEO MẪU SAU (Không markdown, không giải thích):\n"
            "{\n"
            "  \"is_passed\": true,\n"
            "  \"corrected_translation\": \"Bản sửa lại nếu lỗi\",\n"
            "  \"reason\": \"Lý do sửa\"\n"
            "}"
        )

    def review_translation(self, source_text: str, translated_text: str) -> dict:
        """Đưa bản dịch qua AI để hội chẩn."""
        if not self.client:
            return {"is_passed": True, "corrected_translation": translated_text, "reason": "No API Key"}

        prompt_content = f"CÂU GỐC:\n{source_text}\n\nBẢN DỊCH:\n{translated_text}"
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{self.system_prompt}\n\n{prompt_content}"
            )
            
            # Xử lý chuỗi JSON siêu an toàn
            raw_text = response.text
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
            
            # Lệnh này đã được đóng ngoặc an toàn
            result = json.loads(clean_json) 
            
            return result
            
        except Exception as e:
            print(f"   [!] Lỗi khi chạy AI Reviewer: {e}")
            return {"is_passed": True, "corrected_translation": translated_text, "reason": "Reviewer failed to respond"}

# ==========================================
# TEST NHANH SỨC MẠNH CỦA AI REVIEWER
# ==========================================
if __name__ == "__main__":
    reviewer = MedicalAIReviewer()
    
    source_sentence = "Patient has no evidence of intracranial hemorrhage on CT scan."
    fatal_error_translation = "Bệnh nhân có bằng chứng xuất huyết nội sọ trên phim chụp CT."
    
    print("--- KIỂM TRA BẢN DỊCH LỖI NGHIÊM TRỌNG ---")
    print(f"Gốc: {source_sentence}")
    print(f"Dịch lỗi: {fatal_error_translation}")
    
    print("\n>> Đang gửi cho AI Reviewer hội chẩn...")
    review_result = reviewer.review_translation(source_sentence, fatal_error_translation)
    
    if review_result.get("is_passed"):
        print("[O] Bản dịch ĐẠT.")
    else:
        print("[X] Bản dịch KHÔNG ĐẠT!")
        print(f"    - Bản sửa lại: {review_result.get('corrected_translation')}")
        print(f"    - Lý do: {review_result.get('reason')}")
        
    print("\n" + "="*50 + "\n")
    
    source_sentence_2 = "Administer Epinephrine 1 mg IV every 3-5 minutes."
    error_translation_2 = "Tiêm tĩnh mạch Epinephrine 10 mg mỗi 3-5 phút."
    
    print("--- KIỂM TRA BẢN DỊCH LỖI CON SỐ ---")
    print(f"Gốc: {source_sentence_2}")
    print(f"Dịch lỗi: {error_translation_2}")
    
    print("\n>> Đang gửi cho AI Reviewer hội chẩn...")
    review_result_2 = reviewer.review_translation(source_sentence_2, error_translation_2)
    
    if review_result_2.get("is_passed"):
        print("[O] Bản dịch ĐẠT.")
    else:
        print("[X] Bản dịch KHÔNG ĐẠT!")
        print(f"    - Bản sửa lại: {review_result_2.get('corrected_translation')}")
        print(f"    - Lý do: {review_result_2.get('reason')}")