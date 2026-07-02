import os
import time
from dotenv import load_dotenv
from google import genai
from sqlalchemy.orm import Session

from models import SessionLocal, TranslationMemory
from core.formula_preserver import FormulaPreserver
from core.segment_engine import SegmentEngine
from core.ai_reviewer import MedicalAIReviewer # <-- Thêm Reviewer

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class MedicalTranslator:
    def __init__(self):
        self.preserver = FormulaPreserver()
        self.segmenter = SegmentEngine()
        self.reviewer = MedicalAIReviewer() # Khởi tạo Bác sĩ giám định
        self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        
        self.system_prompt = (
            "Bạn là bác sĩ chuyên khoa cấp 1 Hồi sức cấp cứu dịch thuật y khoa. "
            "Hãy dịch câu tiếng Anh sau sang tiếng Việt. "
            "TUÂN THỦ: \n"
            "- Giữ nguyên các thẻ mặt nạ như [[MASK_0]].\n"
            "- Dùng 'hệ thần kinh đối giao cảm', tuyệt đối không dùng 'phó giao cảm'.\n"
            "- Giữ nguyên các thuật ngữ lâm sàng như 'HBc total'.\n"
            "Chỉ trả về đúng câu dịch, không giải thích."
        )

    def translate_segment(self, db: Session, raw_segment: str) -> str:
        # 1. Đeo mặt nạ bảo vệ công thức/chỉ số
        masked_text, mapping_dict = self.preserver.mask(raw_segment)
        
        # 2. Tạo mã băm (Hash)
        segment_hash = self.segmenter.generate_hash(masked_text)
        
        # 3. Tra cứu Database
        cached_translation = db.query(TranslationMemory).filter(TranslationMemory.source_hash == segment_hash).first()
        
        if cached_translation:
            print(f"   [⚡ CACHE HIT] Lấy từ Bộ nhớ dịch.")
            cached_translation.usage_count += 1
            db.commit()
            return self.preserver.unmask(cached_translation.target_segment, mapping_dict)
            
        # 4. Gọi Gemini dịch
        print(f"   [🤖 API CALL] Đang dịch câu mới...")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{self.system_prompt}\n\nCâu gốc:\n{masked_text}"
            )
            translated_masked_text = response.text.strip()
            
            # --- 4.5. KIỂM DUYỆT BỞI AI REVIEWER ---
            print(f"   [🔍 REVIEW] Đang kiểm duyệt bản dịch...")
            review_result = self.reviewer.review_translation(masked_text, translated_masked_text)
            
            if not review_result.get("is_passed"):
                # Nếu không đạt, lấy bản đã được AI Reviewer sửa
                print(f"      -> Phát hiện lỗi: {review_result.get('reason')}")
                translated_masked_text = review_result.get("corrected_translation", translated_masked_text)
            else:
                print(f"      -> Đạt chuẩn.")
            
            # 5. Lưu vào Database
            new_tm_entry = TranslationMemory(
                source_segment=masked_text,
                source_hash=segment_hash,
                target_segment=translated_masked_text,
                is_verified=True # Đánh dấu là đã qua kiểm duyệt
            )
            db.add(new_tm_entry)
            db.commit()
            
            # 6. Tháo mặt nạ và trả về
            return self.preserver.unmask(translated_masked_text, mapping_dict)
            
        except Exception as e:
            print(f"   [!] Lỗi khi dịch: {e}")
            return raw_segment