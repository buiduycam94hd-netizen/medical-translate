import os
import logging
import asyncio
import base64
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import fitz  
from google import genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI(title="MedicalTranslate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Đang bóc tách file PDF...', 'percent': 10})}\n\n"
            
            file_content = await file.read()
            doc = fitz.open(stream=file_content, filetype="pdf")
            num_pages = len(doc)
            
            if num_pages == 0:
                yield f"data: {json.dumps({'type': 'error', 'message': 'File PDF rỗng hoặc bị hỏng.'})}\n\n"
                return

            full_original_text = ""
            full_translated_text = ""
            translated_pages_list = []
            
            client = genai.Client(api_key=API_KEY) if API_KEY else None
            max_pages_to_translate = min(num_pages, 3) 

            for page_num in range(max_pages_to_translate):
                percent = 10 + int((page_num / max_pages_to_translate) * 70)
                yield f"data: {json.dumps({'type': 'progress', 'message': f'Đang dịch trang {page_num + 1}/{max_pages_to_translate}...', 'percent': percent})}\n\n"
                
                page_text = doc.load_page(page_num).get_text()
                if not page_text.strip():
                    translated_pages_list.append("")
                    continue 
                    
                full_original_text += f"\n\n--- TRANG {page_num + 1} ---\n\n{page_text}"
                
                if client:
                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=f"Dịch đoạn văn y khoa sau sang tiếng Việt. Chỉ trả lời bản dịch, không giải thích:\n\n{page_text}"
                        )
                        translated_text = response.text
                        full_translated_text += f"\n\n--- TRANG {page_num + 1} ---\n\n{translated_text}"
                        translated_pages_list.append(translated_text)
                    except Exception as ai_error:
                        logger.error(f"Lỗi ở trang {page_num + 1}: {ai_error}")
                        err_msg = f"[Lỗi AI: {str(ai_error)}]"
                        full_translated_text += f"\n\n--- TRANG {page_num + 1} ---\n{err_msg}"
                        translated_pages_list.append(err_msg)
                    
                    if page_num < max_pages_to_translate - 1:
                        yield f"data: {json.dumps({'type': 'progress', 'message': 'Đang tạm nghỉ 15s để làm mát hệ thống AI...', 'percent': percent + 5})}\n\n"
                        await asyncio.sleep(15)
                else:
                    full_translated_text = "[Lỗi]: Chưa cấu hình API Key."
                    translated_pages_list.append("[Lỗi]: Chưa cấu hình API Key.")

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Đang tạo file PDF bản dịch Tiếng Việt...', 'percent': 90})}\n\n"
            
            # --- THUẬT TOÁN TẠO PDF CHỐNG TRÀN CHỮ ---
            out_pdf = fitz.open()
            font_path = "C:/Windows/Fonts/arial.ttf" 
            
            for text in translated_pages_list:
                if not text or not text.strip():
                    text = "[Lỗi: Trang này trống dữ liệu dịch]"

                fontsize = 12
                is_fitted = False
                
                # Nháp: Giảm cỡ chữ dần từ 12 xuống 6
                while fontsize >= 6:
                    page = out_pdf.new_page()
                    try:
                        page.insert_font(fontname="ArialVN", fontfile=font_path)
                        use_font = "ArialVN"
                    except Exception:
                        use_font = "helv" 
                        
                    rect = fitz.Rect(40, 40, page.rect.width - 40, page.rect.height - 40)
                    
                    # Hàm này trả về số < 0 nếu chữ bị tràn khỏi khung
                    rc = page.insert_textbox(rect, text, fontsize=fontsize, fontname=use_font)
                    
                    if rc >= 0:
                        is_fitted = True
                        break # Vừa vặn, giữ nguyên trang này
                    else:
                        out_pdf.delete_page(page.number) # Bị tràn, xóa trang nháp làm lại
                        fontsize -= 1
                
                # Nếu cỡ 6 vẫn tràn (văn bản quá dài), ép chèn vào
                if not is_fitted:
                    page = out_pdf.new_page()
                    try:
                        page.insert_font(fontname="ArialVN", fontfile=font_path)
                    except: pass
                    page.insert_textbox(rect, text, fontsize=6, fontname=use_font)
                    
            pdf_bytes = out_pdf.write()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

            yield f"data: {json.dumps({'type': 'success', 'filename': file.filename, 'pages': num_pages, 'original_text': full_original_text, 'translated_text': full_translated_text, 'pdf_base64': pdf_base64, 'message': f'Đã dịch và ghép thành công {max_pages_to_translate} trang.', 'percent': 100})}\n\n"
            
        except Exception as e:
            logger.error(f"Lỗi hệ thống: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Lỗi hệ thống: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")