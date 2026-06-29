from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  

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
    return {"message": "Hello World! Backend FastAPI đã kết nối thành công với Frontend."}

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        
        # Mở file PDF
        doc = fitz.open(stream=file_content, filetype="pdf")
        num_pages = len(doc)
        
        # Trích xuất nội dung trang đầu tiên (trang số 0 trong lập trình)
        first_page_text = ""
        if num_pages > 0:
            page = doc.load_page(0)
            first_page_text = page.get_text()
            
            # Cắt ngắn bớt nếu chữ quá dài để API không bị quá tải
            if len(first_page_text) > 500:
                first_page_text = first_page_text[:500] + "...\n[ĐÃ CẮT BỚT]"

        return {
            "status": "success",
            "filename": file.filename,
            "pages": num_pages,
            "first_page_preview": first_page_text, # Gửi phần chữ vừa trích xuất về
            "message": f"Đã tải lên thành công file PDF có {num_pages} trang."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}