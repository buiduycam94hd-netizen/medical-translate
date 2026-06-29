"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [apiMessage, setApiMessage] = useState("Đang kết nối...");
  const [statusColor, setStatusColor] = useState("text-yellow-600");
  
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Trạng thái cho thanh tiến trình
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState("");

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

  const handleUpload = async () => {
    if (!file) return alert("Vui lòng chọn file PDF!");
    
    setIsUploading(true);
    setUploadResult(null);
    setProgress(0);
    setProgressText("Bắt đầu tải lên...");
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload/", {
        method: "POST",
        body: formData,
      });

      // Đọc dữ liệu dạng luồng (Stream)
      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      let partialData = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          partialData += decoder.decode(value, { stream: true });
          const lines = partialData.split("\n\n");
          
          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i];
            if (line.startsWith("data: ")) {
              try {
                const dataStr = line.replace("data: ", "");
                const data = JSON.parse(dataStr);
                
                if (data.type === "progress") {
                  setProgress(data.percent);
                  setProgressText(data.message);
                } else if (data.type === "success") {
                  setUploadResult(data);
                  setProgress(100);
                  setProgressText("Hoàn tất!");
                } else if (data.type === "error") {
                  alert(data.message);
                }
              } catch (e) {
                console.error("Lỗi parse JSON", e);
              }
            }
          }
          partialData = lines[lines.length - 1];
        }
      }
    } catch (error) {
      alert("Lỗi mạng: Không thể kết nối tới Backend!");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadPDF = () => {
    if (!uploadResult?.pdf_base64) return;
    const linkSource = `data:application/pdf;base64,${uploadResult.pdf_base64}`;
    const downloadLink = document.createElement("a");
    downloadLink.href = linkSource;
    downloadLink.download = `BanDich_${file?.name || "MedicalTranslate.pdf"}`;
    downloadLink.click();
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-12 bg-gray-50">
      <h1 className="text-4xl font-bold text-blue-600 mb-2">MedicalTranslate</h1>
      <p className="text-lg text-gray-700 mb-8">Hệ thống dịch thuật PDF Y khoa Anh - Việt</p>
      
      <div className="p-4 bg-white rounded-lg shadow-md border border-gray-200 w-full max-w-4xl mb-6 flex justify-between items-center">
        <p className="text-sm font-medium text-gray-500">Trạng thái API:</p>
        <p className={`font-bold ${statusColor}`}>{apiMessage}</p>
      </div>

      <div className="p-6 bg-white rounded-lg shadow-md border border-gray-200 w-full max-w-4xl">
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
            {isUploading ? "Đang xử lý..." : "Tải lên & Dịch"}
          </button>
        </div>

        {/* HIỂN THỊ THANH TIẾN TRÌNH KHI ĐANG UPLOAD */}
        {isUploading && (
          <div className="mt-6 p-4 bg-blue-50 rounded-md border border-blue-100">
            <div className="flex justify-between text-sm text-blue-800 font-medium mb-2">
              <span>{progressText}</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* KẾT QUẢ TRẢ VỀ */}
        {!isUploading && uploadResult && uploadResult.pdf_base64 && (
          <div className="mt-6 border-t pt-4">
            <div className="flex justify-between items-center mb-4">
              <p className="font-semibold text-green-600">✓ {uploadResult.message}</p>
              <button 
                onClick={handleDownloadPDF}
                className="px-4 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 transition-colors shadow-sm"
              >
                📥 Tải PDF Bản Dịch
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500 mb-2">Bản gốc (Tiếng Anh):</p>
                <div className="bg-gray-100 p-4 rounded-md text-sm text-gray-800 h-96 overflow-y-auto whitespace-pre-wrap font-mono border border-gray-300">
                  {uploadResult.original_text}
                </div>
              </div>
              
              <div>
                <p className="text-sm font-medium text-blue-600 mb-2">Bản dịch (Tiếng Việt):</p>
                <div className="bg-blue-50 p-4 rounded-md text-sm text-gray-800 h-96 overflow-y-auto whitespace-pre-wrap font-sans border border-blue-200">
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