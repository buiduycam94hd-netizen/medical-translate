import os
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import re
from dotenv import load_dotenv
from google import genai

# --- THƯ VIỆN SURYA OCR ---
from surya.ocr import run_ocr
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

print("Đang tải 'đôi mắt' Surya OCR...")
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()

def translate_pdf_keep_layout(input_pdf_path, output_pdf_path):
    doc = fitz.open(input_pdf_path)
    
    for page_num in range(len(doc)):
        print(f"\n--- Đang xử lý trang {page_num + 1}/{len(doc)} ---")
        page = doc[page_num]
        
        # 1. Render trang thành ảnh
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        scale_x = page.rect.width / image.width
        scale_y = page.rect.height / image.height

        # 2. Quét OCR
        print(">> Đang quét tọa độ chữ...")
        predictions = run_ocr([image], [["en"]], det_model, det_processor, rec_model, rec_processor)
        
        text_lines = predictions[0].text_lines
        if not text_lines:
            continue
            
        items_to_translate = []
        for i, line in enumerate(text_lines):
            # Lấy toàn bộ chữ (kể cả chữ ngắn như NO, IV)
            if len(line.text.strip()) > 0:
                items_to_translate.append({
                    "id": i,
                    "text": line.text,
                    "bbox": line.bbox 
                })

        if not items_to_translate:
            continue

        # 3. Dịch qua Gemini (Chia lô & Xử lý JSON mạnh)
        batch_size = 15
        vi_dict = {}
        
        print(f">> Bắt đầu dịch {len(items_to_translate)} khối chữ...")
        
        for i in range(0, len(items_to_translate), batch_size):
            batch = items_to_translate[i:i+batch_size]
            print(f"   - Đang dịch lô từ {i+1} đến {min(i+batch_size, len(items_to_translate))}...")
            
            source_texts = json.dumps([{"id": item["id"], "text": item["text"]} for item in batch], ensure_ascii=False)
            
            system_prompt = (
                "Bạn là bác sĩ chuyên khoa cấp 1 Hồi sức cấp cứu. "
                "Hãy dịch mảng JSON chứa các khối chữ tiếng Anh trích xuất từ PDF y khoa sau sang tiếng Việt. "
                "Giữ nguyên ký hiệu lâm sàng chuẩn xác (vd: HBc total) và ưu tiên dùng thuật ngữ 'hệ thần kinh đối giao cảm'. "
                "BẮT BUỘC TRẢ VỀ JSON HỢP LỆ THEO CẤU TRÚC: [{\"id\": <id gốc>, \"text\": \"<chữ đã dịch>\"}]. "
                "Không giải thích, không dùng markdown."
            )
            
            try:
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"{system_prompt}\n\nDữ liệu gốc:\n{source_texts}"
                )
                
                # Dùng Regex để ép bóc tách mảng JSON, loại bỏ mọi rác xung quanh
                match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if match:
                    clean_json = match.group(0)
                    translated_items = json.loads(clean_json)
                    
                    for item in translated_items:
                        if "id" in item and "text" in item:
                            # Ép kiểu int cho ID để đảm bảo khớp 100%
                            vi_dict[int(item["id"])] = item["text"]
                else:
                    print("   [!] Lỗi: AI không trả về mảng JSON hợp lệ.")
                        
                time.sleep(2) # Tăng thời gian nghỉ lên 2s để tránh bị Google chặn API
            except Exception as e:
                print(f"   [!] Lỗi kết nối hoặc xử lý ở lô này: {e}")

        # Kiểm tra nếu AI không dịch được gì
        if not vi_dict:
            print(">> [CẢNH BÁO] Không có dữ liệu tiếng Việt nào được trả về. Bỏ qua trang này.")
            continue

        # 4. Ghi đè tiếng Việt lên PDF
        print(f">> Đang tái tạo Layout với {len(vi_dict)} khối chữ...")
        try:
            page.insert_font(fontname="vi_arial", fontfile="C:/Windows/Fonts/arial.ttf")
            used_font = "vi_arial"
        except:
            used_font = "helv"
            
        for item in items_to_translate:
            if item["id"] in vi_dict:
                vi_text = vi_dict[item["id"]]
                x1, y1, x2, y2 = item["bbox"]
                
                rect = fitz.Rect(x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y)
                
                # --- LẤY MẪU MÀU KÈM BỘ LỌC TRẮNG ---
                sample_x = min(int(x1 + 2), image.width - 1)
                sample_y = min(int(y1 + 2), image.height - 1)
                try:
                    r, g, b = image.getpixel((sample_x, sample_y))
                    if r > 240 and g > 240 and b > 240:
                        bg_color = (1, 1, 1)
                    else:
                        bg_color = (r/255.0, g/255.0, b/255.0)
                except:
                    bg_color = (1, 1, 1)
                
                # Xóa nền
                page.draw_rect(rect, color=bg_color, fill=bg_color)
                
                # --- TÍNH TỌA ĐỘ VÀ CỠ CHỮ ---
                box_width = rect.width
                box_height = rect.height
                
                text_rect = rect + (-2, -2, 2, 2)
                
                if box_width > 4 * box_height:
                    text_align = 0 
                    dynamic_fontsize = 10.0 
                else:
                    text_align = 1 
                    dynamic_fontsize = box_height * 0.55 
                    dynamic_fontsize = max(5.0, min(dynamic_fontsize, 11.0))
                
                # In chữ mới
                page.insert_textbox(
                    text_rect, 
                    vi_text, 
                    fontsize=dynamic_fontsize, 
                    fontname=used_font, 
                    color=(0, 0, 0),
                    align=text_align 
                )

    doc.save(output_pdf_path)
    print(f"\n[THÀNH CÔNG] Đã xuất file PDF dịch tại: {output_pdf_path}")

if __name__ == "__main__":
    input_file = "input.pdf"
    output_file = "output_translated.pdf"
    if os.path.exists(input_file):
        translate_pdf_keep_layout(input_file, output_file)
    else:
        print(f"Vui lòng chép {input_file} vào thư mục để chạy thử.")