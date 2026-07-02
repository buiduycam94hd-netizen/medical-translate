import re
import hashlib

class SegmentEngine:
    def __init__(self):
        # 1. Danh sách các từ viết tắt học thuật/y khoa cấm ngắt câu
        # (Cứ thấy dấu chấm sau các từ này thì không được cắt)
        self.protected_abbrs = (
            "al.", "fig.", "dr.", "vs.", "e.g.", "i.e.", "vol.", "no.", 
            "ed.", "et.", "iv.", "prof.", "inc.", "ltd.", "st.", "mt.", "eq."
        )

    def clean_pdf_text(self, raw_text: str) -> str:
        """
        Khử nhiễu rác từ PDF: 
        - Nối các từ bị cắt đôi bởi dấu gạch ngang ở cuối dòng
        - Ép các dòng bị vỡ về thành một đoạn văn liền mạch
        """
        # Nối từ bị gạch nối (VD: "in- \n formation" -> "information")
        text = re.sub(r'-\s*\n\s*', '', raw_text)
        
        # Thay thế mọi dấu xuống dòng/nhiều khoảng trắng liên tiếp bằng đúng 1 khoảng trắng
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def split_sentences(self, text: str) -> list:
        """
        Thuật toán ngắt câu thông minh, né các từ viết tắt y khoa
        """
        cleaned = self.clean_pdf_text(text)
        
        # Tách thô: Tách tại các dấu chấm/hỏi/chấm than (. ! ?) mà theo sau là khoảng trắng
        raw_chunks = re.split(r'(?<=[.!?])\s+', cleaned)
        
        sentences = []
        current_sentence = ""

        for chunk in raw_chunks:
            if not chunk:
                continue
            
            # Ghép chunk hiện tại vào câu đang xử lý
            if current_sentence:
                current_sentence += " " + chunk
            else:
                current_sentence = chunk
            
            # Kiểm tra xem đuôi của câu hiện tại có bị rơi vào bẫy "từ viết tắt" không
            lower_sent = current_sentence.lower()
            is_abbreviation = any(lower_sent.endswith(abbr) for abbr in self.protected_abbrs)
            
            # Chống lỗi ngắt sai ở các danh sách liệt kê (VD: "A. ", "B. ")
            is_single_letter = re.search(r'\b[a-z]\.$', lower_sent)
            
            # Nếu KHÔNG phải từ viết tắt, đây là một câu hoàn chỉnh -> Chốt câu!
            if not is_abbreviation and not is_single_letter:
                sentences.append(current_sentence.strip())
                current_sentence = ""
                
        # Nếu đoạn text bị cụt ở cuối (không có dấu chấm kết thúc), vẫn gom lại thành 1 câu
        if current_sentence:
            sentences.append(current_sentence.strip())
            
        return sentences

    def generate_hash(self, text: str) -> str:
        """Tạo mã MD5 để lưu vào Database Translation Memory"""
        clean_text = text.strip().lower() 
        return hashlib.md5(clean_text.encode('utf-8')).hexdigest()

# ==========================================
# TEST NHANH MODULE NÀY
# ==========================================
if __name__ == "__main__":
    engine = SegmentEngine()
    
    # Một đoạn text "mô phỏng" bị vỡ nát khi đọc từ PDF (có gạch nối, xuống dòng lung tung)
    # và chứa đầy cạm bẫy viết tắt (et al., Fig., e.g.)
    messy_pdf_text = """
    In a recent study by Macdonald et al. the use of IV. fluids was 
    com-
    pared with early vasopressors. This is shown in Fig. 1. Patients re-
    ceived large volumes (e.g. 30 ml/kg) in the control group! Did it 
    improve survival? No.
    """
    
    print("--- 1. TEXT GỐC TỪ PDF (BỊ VỠ NÁT) ---")
    print(messy_pdf_text)
    
    print("\n--- 2. SAU KHI QUA SEGMENT ENGINE (KHỬ NHIỄU & CẮT CÂU) ---")
    sentences = engine.split_sentences(messy_pdf_text)
    
    for i, sent in enumerate(sentences, 1):
        # Tạo mã Hash cho câu này để tra cứu Database
        db_hash = engine.generate_hash(sent)
        print(f"\n[Câu {i}] (Hash: {db_hash[:8]}...)")
        print(f"Nội dung: {sent}")