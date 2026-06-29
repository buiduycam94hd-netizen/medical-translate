"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [apiMessage, setApiMessage] = useState("Đang kết nối...");
  const [statusColor, setStatusColor] = useState("text-yellow-600");
  
  // Các biến dùng để xử lý file PDF
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Kiểm tra kết nối API
  useEffect(() => {
    fetch("http://127.0.0.1:8000/")
      .then((res) => res.json())
      .then(() => {
        setApiMessage("Đã kết nối Backend");
        setStatusColor("text-green-600");
      })
      .catch(() => {
        setApiMessage("Lỗi kết nối tới Backend!");
        setStatusColor("text-red-600");
      });
  }, []);

  // Hàm xử lý khi bấm nút "Tải lên"
  const handleUpload = async () => {
    if (!file) return alert("Vui lòng chọn file PDF!");
    setIsUploading(true);
    
    // Đóng gói file để gửi đi
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload/", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setUploadResult(data); // Lưu kết quả Backend trả về
    } catch (error) {
      alert("Lỗi khi tải file lên!");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-12 bg-gray-50">
      <h1 className="text-4xl font-bold text-blue-600 mb-2">MedicalTranslate</h1>
      <p className="text-lg text-gray-700 mb-8">Hệ thống dịch thuật PDF Y khoa Anh - Việt</p>
      
      <div className="p-4 bg-white rounded-lg shadow-md border border-gray-200 w-full max-w-2xl mb-6 flex justify-between items-center">
        <p className="text-sm font-medium text-gray-500">Trạng thái API:</p>
        <p className={`font-bold ${statusColor}`}>{apiMessage}</p>
      </div>

      {/* Khu vực Upload File */}
      <div className="p-6 bg-white rounded-lg shadow-md border border-gray-200 w-full max-w-2xl">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Tải lên tài liệu PDF</h2>
        <div className="flex gap-4">
          <input 
            type="file" 
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
          />
          <button 
            onClick={handleUpload}
            disabled={isUploading}
            className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400 whitespace-nowrap transition-colors"
          >
            {isUploading ? "Đang xử lý..." : "Tải lên"}
          </button>
        </div>

        {/* Khu vực hiển thị kết quả */}
        {uploadResult && uploadResult.status === "success" && (
          <div className="mt-6 border-t pt-4">
            <p className="font-semibold text-green-600 mb-3">✓ {uploadResult.message}</p>
            
            <div className="grid grid-cols-2 gap-4">
              {/* Cột Tiếng Anh */}
              <div>
                <p className="text-sm font-medium text-gray-500 mb-2">Bản gốc (Tiếng Anh):</p>
                <div className="bg-gray-100 p-4 rounded-md text-sm text-gray-800 h-64 overflow-y-auto whitespace-pre-wrap font-mono border border-gray-300">
                  {uploadResult.original_text}
                </div>
              </div>
              
              {/* Cột Tiếng Việt */}
              <div>
                <p className="text-sm font-medium text-blue-600 mb-2">Bản dịch (Tiếng Việt):</p>
                <div className="bg-blue-50 p-4 rounded-md text-sm text-gray-800 h-64 overflow-y-auto whitespace-pre-wrap font-sans border border-blue-200">
                  {uploadResult.translated_text}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}