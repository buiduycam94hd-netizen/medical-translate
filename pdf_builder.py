import os
import time
import fitz  # PyMuPDF
from PIL import Image
import io

# --- ĐÔI MẮT: SURYA OCR ---
from surya.ocr import run_ocr
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

# --- BỘ NÃO: MEDICAL CAT CORE ---
from translator_service import MedicalTranslator
from models import SessionLocal

print("Đang khởi động hệ thống Medical CAT Platform...")
print("Đang tải 'đôi mắt' Surya OCR (Vui lòng đợi vài giây)...")
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()
print("Sẵn sàng xuất xưởng PDF!")

def build_bilingual_pdf(input_pdf_path, output_pdf_path):
    # Mở file PDF gốc
    doc = fitz.open(input_pdf_path)
    
    # Tạo file PDF HOÀN TOÀN MỚI để chứa cấu trúc Song Ngữ
    out_doc = fitz.open() 
    
    # Khởi động Động cơ dịch thuật và kết nối Database
    translator = MedicalTranslator()
    db = SessionLocal()
    
    for page_num in range(len(doc)):
        print(f"\n--- Đang xử lý trang {page_num + 1}/{len(doc)} ---")
        original_page = doc[page_num]
        
        # 1. Chèn TRANG GỐC (Tiếng Anh) vào file mới
        out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        # 2. Chèn thêm một TRANG COPY (Nằm ngay sau trang gốc) để làm bản Tiếng Việt
        out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        vi_page = out_doc[-1] # Lấy trang vừa chép (nằm ở cuối cùng hiện tại) để thao tác
        
        # Render ảnh để Surya quét
        pix = original_page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        scale_x = original_page.rect.width / image.width
        scale_y = original_page.rect.height / image.height

        # OCR
        print(">> Đang quét tọa độ chữ...")
        predictions = run_ocr([image], [["en"]], det_model, det_processor, rec_model, rec_processor)
        
        text_lines = predictions[0].text_lines
        if not text_lines:
            continue
            
        try:
            vi_page.insert_font(fontname="vi_arial", fontfile="C:/Windows/Fonts/arial.ttf")
            used_font = "vi_arial"
        except:
            used_font = "helv"

        print(f">> Bắt đầu dịch & tái tạo Layout ({len(text_lines)} khối chữ)...")
        
        for i, line in enumerate(text_lines):
            raw_text = line.text.strip()
            if len(raw_text) == 0:
                continue
                
            print(f"\n   --- Khối {i+1}/{len(text_lines)} ---")
            
            # GỌI TRÁI TIM CỦA HỆ THỐNG: 
            # Tự động đi qua Masking -> TM Database -> Gemini -> AI Reviewer -> Unmasking
            vi_text = translator.translate_segment(db, raw_text)
            
            # ĐỘ TRỄ BẢO VỆ API: Ngăn Google chặn lỗi 429 Resource Exhausted.
            # Vì luồng này xử lý từng câu liên tục, nghỉ 3 giây là bắt buộc đối với gói Free.
            time.sleep(3) 
            
            # --- TÁI TẠO LAYOUT LÊN TRANG TIẾNG VIỆT (vi_page) ---
            x1, y1, x2, y2 = line.bbox
            rect = fitz.Rect(x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y)
            
            # Lấy màu nền + Bộ lọc cân bằng trắng
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
            
            # Quét lớp sơn nền để xóa chữ tiếng Anh
            vi_page.draw_rect(rect, color=bg_color, fill=bg_color)
            
            # Thuật toán Căn lề và Tính font động
            box_width = rect.width
            box_height = rect.height
            text_rect = rect + (-2, -2, 2, 2)
            
            if box_width > 4 * box_height:
                text_align = 0 # Căn trái cho đoạn văn
                dynamic_fontsize = 10.0 
            else:
                text_align = 1 # Căn giữa cho sơ đồ/bảng
                dynamic_fontsize = box_height * 0.55 
                dynamic_fontsize = max(5.0, min(dynamic_fontsize, 11.0))
            
            # Bơm chữ tiếng Việt vào
            vi_page.insert_textbox(
                text_rect, 
                vi_text, 
                fontsize=dynamic_fontsize, 
                fontname=used_font, 
                color=(0, 0, 0),
                align=text_align 
            )

    # Đóng kết nối DB và lưu file
    db.close()
    out_doc.save(output_pdf_path)
    print(f"\n[THÀNH CÔNG] Đã xuất file PDF Song Ngữ tại: {output_pdf_path}")

if __name__ == "__main__":
    # Bạn hãy chuẩn bị sẵn file input.pdf trong thư mục nhé
    input_file = "input.pdf"
    output_file = "output_bilingual.pdf"
    
    if os.path.exists(input_file):
        build_bilingual_pdf(input_file, output_file)
    else:
        print(f"Vui lòng chép file {input_file} vào thư mục để chạy.")