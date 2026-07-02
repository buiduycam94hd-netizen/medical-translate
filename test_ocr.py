from PIL import Image
from surya.ocr import run_ocr
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

def test_ocr(image_path):
    print("Đang khởi động 'đôi mắt' Surya Classic (chạy hoàn toàn bằng Python)...")
    
    # Khai báo ngôn ngữ cần nhận diện (tiếng Anh)
    langs = [["en"]]
    
    # Tải mô hình nhận diện và bóc tách
    det_processor, det_model = load_det_processor(), load_det_model()
    rec_model, rec_processor = load_rec_model(), load_rec_processor()
    
    # Đọc ảnh
    image = Image.open(image_path)
    
    # Bắt đầu quét
    print("Đang quét và bóc tách chữ...")
    predictions = run_ocr([image], langs, det_model, det_processor, rec_model, rec_processor)
    
    # In kết quả ra màn hình
    print("\n--- KẾT QUẢ BÓC TÁCH ---")
    for text_line in predictions[0].text_lines:
        print(f"- {text_line.text}")

if __name__ == "__main__":
    img_path = "test_image.png" 
    try:
        test_ocr(img_path)
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")