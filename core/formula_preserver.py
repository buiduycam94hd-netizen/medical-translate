import re

class FormulaPreserver:
    def __init__(self):
        # 1. TẬP HỢP CÁC QUY TẮC NHẬN DIỆN (REGEX)
        self.patterns = [
            # Bắt các biểu thức toán học và chỉ số có đơn vị (vd: < 65 mmHg, > 2.0 mmol/L, 30 mL/kg, 3-4 L)
            r'([<>=≤≥~]?\s*\d+(?:\.\d+)?\s*(?:mmHg|mmol/L|mL/kg|mg/dL|L|min|h|%))',
            
            # Bắt các công thức khí máu, điện giải (vd: PaO2, SpO2, Na+, HCO3-, pH, FiO2)
            r'\b(PaO2|SpO2|FiO2|SaO2|Na\+|K\+|Ca2\+|Cl-|HCO3-|pH|pCO2)\b',
            
            # Bắt các từ viết tắt Y khoa/Chỉ số cận lâm sàng cấm dịch (vd: MAP, SBP, IV, ICU, ED, EGDT, AKI, ARDS, HBc total)
            r'\b(MAP|SBP|DBP|HR|IV|ICU|ED|EGDT|AKI|ARDS|STEMI|NSTEMI|ECG|HBc total|DAOH90)\b',
            
            # Bắt các cụm biểu thức có dấu (vd: SBP < 90 mmHg) - Bắt chùm lớn để an toàn hơn
            r'\b([A-Z]{2,4}\s*[<>=≤≥]\s*\d+(?:\.\d+)?\s*[a-zA-Z/]+)\b'
        ]
        
        # Gộp tất cả các luật regex lại thành một màng lọc khổng lồ
        self.combined_pattern = re.compile('|'.join(self.patterns))

    def mask(self, text: str):
        """
        Quét văn bản, thay thế các công thức/chỉ số bằng [MASK_X]
        Trả về: (văn_bản_đã_che_mặt_nạ, từ_điển_chứa_giá_trị_gốc)
        """
        mapping_dict = {}
        mask_counter = 0
        
        def replacer(match):
            nonlocal mask_counter
            original_text = match.group(0)
            
            # Nếu biểu thức này đã được mask rồi thì dùng lại mask cũ
            for key, val in mapping_dict.items():
                if val == original_text:
                    return key
                    
            mask_tag = f"[[MASK_{mask_counter}]]"
            mapping_dict[mask_tag] = original_text
            mask_counter += 1
            return mask_tag

        # Áp dụng thay thế bằng Regex
        masked_text = self.combined_pattern.sub(replacer, text)
        return masked_text, mapping_dict

    def unmask(self, masked_text: str, mapping_dict: dict) -> str:
        """
        Nhận lại văn bản sau khi AI dịch xong, và ráp các công thức gốc vào đúng vị trí [MASK_X]
        """
        restored_text = masked_text
        for mask_tag, original_value in mapping_dict.items():
            restored_text = restored_text.replace(mask_tag, original_value)
        return restored_text

# ==========================================
# TEST NHANH MODULE NÀY
# ==========================================
if __name__ == "__main__":
    preserver = FormulaPreserver()
    
    # Lấy thử một câu cực khó từ bài báo của bạn
    sample_text = "Septic shock is characterised clinically by the requirement for vasopressors to maintain a MAP of 65 mmHg and a blood lactate >2 mmol/L that persists after IV fluid resuscitation."
    
    print("--- 1. CÂU GỐC ---")
    print(sample_text)
    
    print("\n--- 2. BƯỚC ĐEO MẶT NẠ (Gửi cho AI câu này) ---")
    masked_text, mapping = preserver.mask(sample_text)
    print(masked_text)
    print(f"(Dữ liệu cất trong két sắt: {mapping})")
    
    # Giả lập AI dịch câu đã đeo mặt nạ
    fake_ai_translation = "Sốc nhiễm khuẩn được đặc trưng trên lâm sàng bởi việc cần sử dụng thuốc vận mạch để duy trì một [[MASK_0]] là [[MASK_1]] và lactate máu [[MASK_2]] vẫn tồn tại sau khi hồi sức bằng dịch [[MASK_3]]."
    
    print("\n--- 3. BƯỚC THÁO MẶT NẠ (Ráp lại sau khi AI dịch xong) ---")
    final_vietnamese = preserver.unmask(fake_ai_translation, mapping)
    print(final_vietnamese)