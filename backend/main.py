from fastapi import FastAPI

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="MedicalTranslate API")

# Tạo một "đường dẫn" (endpoint) cơ bản nhất
@app.get("/")
def read_root():
    return {"message": "Hello World! Hệ thống MedicalTranslate đã khởi động thành công."}