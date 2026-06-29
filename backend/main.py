import os
import logging
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from google import genai
from dotenv import load_dotenv

# 1. Cấu hình hệ thống ghi nhận lỗi (Log) để in ra Terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Tải biến môi trường
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# 3. Khởi tạo FastAPI
app = FastAPI(title="MedicalTranslate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello World! Backend đang chạy tốt."}

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        logger.info(f"--- BẮT ĐẦU XỬ LÝ FILE: {file.filename} ---")
        
        # Bước 1: Đọc PDF
        file_content = await file.read()
        doc = fitz.open(stream=file_content, filetype="pdf")
        num_pages = len(doc)
        logger.info(f"Đã đọc xong PDF. Số trang: {num_pages}")
        
        if num_pages == 0:
            return {"status": "error", "message": "File PDF rỗng hoặc bị hỏng."}
            
        first_page_text = doc.load_page(0).get_text()
        text_to_translate = first_page_text[:500] if len(first_page_text) > 500 else first_page_text
        
        # Bước 2: Gọi Gemini AI
        translated_text = ""
        if not API_KEY:
            translated_text = "[Lỗi]: Chưa có API Key. Hãy kiểm tra lại file .env"
            logger.warning("Không tìm thấy API_KEY.")
        else:
            try:
                logger.info("Đang kết nối với Google Gemini...")
                client = genai.Client(api_key=API_KEY)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Dịch đoạn văn y khoa sau sang tiếng Việt chuyên ngành hồi sức: {text_to_translate}"
                )
                translated_text = response.text
                logger.info("Dịch thành công!")
            except Exception as ai_error:
                # Bắt gọn lỗi AI và biến nó thành chữ để hiển thị lên Web
                error_msg = str(ai_error)
                logger.error(f"Lỗi Gemini: {error_msg}")
                translated_text = f"[Hệ thống báo lỗi AI]: {error_msg}"

        logger.info("--- HOÀN TẤT XỬ LÝ ---")
        
        # Bước 3: Trả kết quả về Web (Luôn trả về success nếu đã đọc được file)
        return {
            "status": "success",
            "filename": file.filename,
            "pages": num_pages,
            "original_text": text_to_translate,
            "translated_text": translated_text,
            "message": "Đã xử lý xong tài liệu."
        }
        
    except Exception as e:
        logger.error(f"Lỗi hệ thống nghiêm trọng: {e}")
        return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}