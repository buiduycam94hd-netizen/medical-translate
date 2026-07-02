import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Index
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. CẤU HÌNH KẾT NỐI POSTGRESQL
# Cú pháp: postgresql://<username>:<password>@<host>:<port>/<database_name>
# Hãy thay '123456' bằng mật khẩu bạn đã đặt ở Bước 1
DATABASE_URL = "postgresql://postgres:123456@localhost:5432/medical_cat_db"

engine = create_engine(DATABASE_URL, echo=True) # echo=True để in log SQL ra Terminal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# BẢNG 1: MEDICAL GLOSSARY (TỪ ĐIỂN Y KHOA)
# ==========================================
class Glossary(Base):
    __tablename__ = "glossaries"

    id = Column(Integer, primary_key=True, index=True)
    source_term = Column(String(255), index=True, nullable=False)  # Từ gốc tiếng Anh (VD: AKI)
    target_term = Column(String(255), nullable=False)              # Từ dịch tiếng Việt (VD: Tổn thương thận cấp)
    
    # Lĩnh vực chuyên khoa (VD: Hồi sức, Chống độc, Tim mạch)
    domain = Column(String(100), default="General")                
    
    # Ghi chú ép LLM tuân thủ (VD: "Không bao giờ dịch là suy thận cấp")
    context_rule = Column(Text, nullable=True)                     
    
    # Đánh dấu cấm dịch (VD: ECG, STEMI, PaO2 -> is_do_not_translate = True)
    is_do_not_translate = Column(Boolean, default=False)           
    
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# BẢNG 2: TRANSLATION MEMORY (BỘ NHỚ DỊCH)
# ==========================================
class TranslationMemory(Base):
    __tablename__ = "translation_memories"

    id = Column(Integer, primary_key=True, index=True)
    
    # Câu/Đoạn văn gốc tiếng Anh (Segment)
    source_segment = Column(Text, nullable=False)
    
    # MÃ BĂM (Hash) của câu gốc. 
    # Giúp Database tìm lại câu đã dịch cực nhanh thay vì phải scan text dài
    source_hash = Column(String(64), index=True, unique=True, nullable=False) 
    
    # Câu dịch tiếng Việt tương ứng
    target_segment = Column(Text, nullable=False)
    
    # Đếm số lần câu này được tái sử dụng (giúp thống kê tiết kiệm chi phí AI)
    usage_count = Column(Integer, default=1)
    
    # AI Reviewer hoặc Bác sĩ đã duyệt câu này chưa?
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_hash(text: str) -> str:
        """Hàm tạo mã băm MD5 chuẩn hóa văn bản trước khi lưu"""
        # Xóa khoảng trắng thừa và đưa về chữ thường để chuẩn hóa
        clean_text = text.strip().lower() 
        return hashlib.md5(clean_text.encode('utf-8')).hexdigest()

# ==========================================
# LỆNH KHỞI TẠO BẢNG TỰ ĐỘNG
# ==========================================
def init_db():
    print("Đang kết nối PostgreSQL và khởi tạo các bảng dữ liệu...")
    Base.metadata.create_all(bind=engine)
    print("Khởi tạo hoàn tất! Bạn có thể mở pgAdmin để kiểm tra.")

if __name__ == "__main__":
    init_db()