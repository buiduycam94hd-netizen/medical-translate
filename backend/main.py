import os
import io
import time
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image
from google import genai

# --- THƯ VIỆN SURYA OCR ---
from surya.ocr import run_ocr
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

# --- 1. TẢI BIẾN MÔI TRƯỜNG ---
# Đảm bảo bạn có file .env cùng thư mục chứa dòng: GEMINI_API_KEY=mã_key_của_bạn
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI(title="Hệ thống Dịch thuật Y khoa & OCR")

# Cấu hình CORS để Next.js (cổng 3000) có thể gửi yêu cầu tới FastAPI (cổng 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. KHỞI TẠO CÁC MODEL AI TOÀN CỤC ---
print("Đang tải các mô hình AI vào bộ nhớ. Vui lòng đợi...")

# Tải Surya OCR (Chỉ tải 1 lần khi bật server để tối ưu tốc độ)
print("[1/2] Đang khởi động đôi mắt AI (Surya OCR)...")
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()

# Khởi tạo client Gemini
print("[2/2] Đang kết nối với não bộ trung tâm (Google Gemini)...")
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print("Tất cả hệ thống AI đã sẵn sàng hoạt động!")
else:
    print("CẢNH BÁO: Chưa tìm thấy GEMINI_API_KEY trong file .env")
    gemini_client = None


# --- 3. CÁC CỔNG GIAO TIẾP (ENDPOINTS) ---

@app.post("/api/ocr")
async def extract_text_from_image(file: UploadFile = File(...)):
    """Đọc và bóc tách văn bản từ hình ảnh tải lên"""
    try:
        start_time = time.time()
        
        # Đọc dữ liệu ảnh
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Quét và bóc tách chữ (Mặc định: tiếng Anh)
        langs = [["en"]]
        predictions = run_ocr([image], langs, det_model, det_processor, rec_model, rec_processor)
        
        # Gom kết quả
        extracted_text = "\n".join([line.text for line in predictions[0].text_lines])
        process_time = round(time.time() - start_time, 2)
        
        return JSONResponse(content={
            "status": "success", 
            "text": extracted_text,
            "process_time_seconds": process_time
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi xử lý ảnh: {str(e)}"}
        )

@app.post("/api/translate")
async def translate_medical_text(text: str = Form(...)):
    """Dịch văn bản y khoa sang tiếng Việt sử dụng Gemini"""
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Chưa cấu hình Gemini API Key trên máy chủ.")
        
    try:
        # Prompt được thiết kế chuyên sâu, chuẩn hóa thuật ngữ lâm sàng
        system_prompt = (
            "Bạn là một bác sĩ chuyên khoa cấp 1 Hồi sức cấp cứu (HSCC). "
            "Hãy dịch đoạn văn bản y khoa sau sang tiếng Việt một cách chính xác, chuẩn văn phong lâm sàng tại bệnh viện Việt Nam. "
            "Lưu ý các nguyên tắc thuật ngữ sau:\n"
            "- Ưu tiên sử dụng 'hệ thần kinh đối giao cảm'.\n"
            "- Giữ nguyên các ký hiệu xét nghiệm chuẩn xác như 'HBc total'.\n"
            "- Đặc biệt chú ý độ chính xác tuyệt đối khi dịch các khái niệm về huyết động, thăng bằng kiềm toan (phương pháp Stewart), và chống độc.\n\n"
            f"Văn bản gốc:\n{text}"
        )
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=system_prompt,
        )
        
        return JSONResponse(content={
            "status": "success",
            "translated_text": response.text
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi dịch thuật từ AI: {str(e)}"}
        )

@app.post("/api/upload-pdf")
async def process_pdf(file: UploadFile = File(...)):
    """Trích xuất văn bản thô từ file PDF"""
    try:
        pdf_bytes = await file.read()
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        full_text = ""
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            full_text += page.get_text() + "\n"
            
        return JSONResponse(content={
            "status": "success",
            "extracted_text": full_text.strip()
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi đọc file PDF: {str(e)}"}
        )