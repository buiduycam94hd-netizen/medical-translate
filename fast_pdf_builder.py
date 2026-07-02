import os
import fitz  # PyMuPDF
import json
import re
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class FastBilingualBuilder:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        
        # Prompt được thiết kế để nhận 1 mảng JSON khổng lồ (Toàn bộ trang)
        self.system_prompt = (
            "Bạn là bác sĩ chuyên khoa cấp 1 HSCC. Dưới đây là mảng JSON chứa các khối văn bản tiếng Anh của MỘT TRANG PDF y khoa. "
            "Hãy dịch toàn bộ giá trị 'text' sang tiếng Việt. "
            "QUY TẮC:\n"
            "- Giữ nguyên các từ viết tắt chuyên ngành (VD: MAP, SBP, ED, ICU).\n"
            "- Dùng 'hệ thần kinh đối giao cảm', không dùng phó giao cảm.\n"
            "- BẮT BUỘC trả về đúng định dạng JSON gốc: [{\"id\": <id>, \"text\": \"<bản dịch>\"}].\n"
            "Không giải thích, không dùng markdown code block."
        )

    def process_document(self, input_pdf, output_pdf):
        doc = fitz.open(input_pdf)
        out_doc = fitz.open()

        for page_num in range(len(doc)):
            print(f"\n--- Đang bóc tách Trang {page_num + 1}/{len(doc)} ---")
            original_page = doc[page_num]
            
            # Chèn trang gốc (Tiếng Anh)
            out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            # Chèn trang copy (Để ghi tiếng Việt)
            out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            vi_page = out_doc[-1]
            
            # 1. TRÍCH XUẤT NGUYÊN BẢN (NATIVE EXTRACTION) THAY VÌ OCR
            # Lấy toàn bộ các khối (blocks) trong trang
            blocks = original_page.get_text("dict")["blocks"]
            
            items_to_translate = []
            
            for b_idx, block in enumerate(blocks):
                # Chỉ lấy các khối chứa văn bản (type == 0)
                if block.get("type") == 0:
                    text_content = ""
                    # Gom tất cả các dòng trong 1 khối lại thành 1 ĐOẠN VĂN hoàn chỉnh
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_content += span["text"] + " "
                            
                    clean_text = text_content.strip()
                    # Bỏ qua các khối rác hoặc quá ngắn
                    if len(clean_text) > 1:
                        items_to_translate.append({
                            "id": b_idx,
                            "text": clean_text,
                            "bbox": block["bbox"] # [x0, y0, x1, y1]
                        })
            
            if not items_to_translate:
                continue

            # 2. DỊCH TOÀN BỘ TRANG TRONG 1 LẦN GỌI API (BATCH TRANSLATION)
            print(f">> Gửi {len(items_to_translate)} đoạn văn cho Gemini (1 Lần Gọi Duy Nhất)...")
            
            # Tách dữ liệu thành các lô lớn (ví dụ 30 đoạn/lô) để tránh quá tải Token của 1 request
            batch_size = 30
            vi_dict = {}
            
            for i in range(0, len(items_to_translate), batch_size):
                batch = items_to_translate[i:i+batch_size]
                source_json = json.dumps([{"id": item["id"], "text": item["text"]} for item in batch], ensure_ascii=False)
                
                try:
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"{self.system_prompt}\n\nDữ liệu gốc:\n{source_json}"
                    )
                    
                    # Trích xuất JSON bằng Regex để chống lỗi markdown
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        translated_items = json.loads(match.group(0))
                        for item in translated_items:
                            vi_dict[int(item["id"])] = item["text"]
                    else:
                        print("   [!] Lỗi Regex: Không bóc tách được JSON.")
                except Exception as e:
                    print(f"   [!] Lỗi API: {e}")
            
            # 3. GHI ĐÈ TIẾNG VIỆT LÊN LAYOUT (VẼ ĐÈ KHỐI)
            print(">> Đang in đè tiếng Việt lên trang...")
            try:
                vi_page.insert_font(fontname="vi_arial", fontfile="C:/Windows/Fonts/arial.ttf")
                used_font = "vi_arial"
            except:
                used_font = "helv"

            for item in items_to_translate:
                b_idx = item["id"]
                if b_idx in vi_dict:
                    rect = fitz.Rect(item["bbox"])
                    vi_text = vi_dict[b_idx]
                    
                    # Tẩy trắng khu vực chữ cũ
                    vi_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                    
                    # Thuật toán co giãn font chữ cho đoạn văn
                    box_width = rect.width
                    box_height = rect.height
                    
                    text_align = 0 if box_width > 3 * box_height else 1
                    dynamic_fontsize = 10.0 if text_align == 0 else max(6.0, box_height * 0.4)
                    
                    # In chữ
                    vi_page.insert_textbox(
                        rect, 
                        vi_text, 
                        fontsize=dynamic_fontsize, 
                        fontname=used_font, 
                        color=(0, 0, 0),
                        align=text_align 
                    )

        out_doc.save(output_pdf)
        print(f"\n[THÀNH CÔNG] Đã lưu file: {output_pdf}")

if __name__ == "__main__":
    input_file = "input.pdf"
    output_file = "output_fast_bilingual.pdf"
    
    if os.path.exists(input_file):
        builder = FastBilingualBuilder()
        builder.process_document(input_file, output_file)
    else:
        print(f"Vui lòng chép file {input_file} vào thư mục.")