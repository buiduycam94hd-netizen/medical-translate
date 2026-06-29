from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # Đây chính là tên thư viện của PyMuPDF khi import

app = FastAPI(title="MedicalTranslate API")

# Cấp quyền CORS cho Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello World! Backend FastAPI đã kết nối thành công với Frontend."}

# API mới: Nhận file PDF và đọc số trang [cite: 20]
@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Đọc dữ liệu file gửi lên
        file_content = await file.read()
        
        # Dùng PyMuPDF mở file trực tiếp từ bộ nhớ 
        doc = fitz.open(stream=file_content, filetype="pdf")
        num_pages = len(doc)
        
        return {
            "status": "success",
            "filename": file.filename,
            "pages": num_pages,
            "message": f"Đã tải lên thành công file PDF có {num_pages} trang."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}