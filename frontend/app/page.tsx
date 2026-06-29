"use client"; // Bắt buộc để dùng tính năng cập nhật trạng thái trong Next.js

import { useEffect, useState } from "react";

export default function Home() {
  // Tạo biến để lưu trạng thái kết nối
  const [apiMessage, setApiMessage] = useState("Đang kết nối...");
  const [statusColor, setStatusColor] = useState("text-yellow-600");

  // Hàm này sẽ tự động chạy 1 lần khi mở trang web
  useEffect(() => {
    // Gọi điện thoại tới Backend ở cổng 8000
    fetch("http://127.0.0.1:8000/")
      .then((res) => res.json())
      .then((data) => {
        // Nhận được câu trả lời thì cập nhật lên màn hình
        setApiMessage(data.message);
        setStatusColor("text-green-600");
      })
      .catch((error) => {
        // Nếu Backend tắt hoặc lỗi
        setApiMessage("Lỗi kết nối tới Backend!");
        setStatusColor("text-red-600");
      });
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-24">
      <h1 className="text-4xl font-bold text-blue-600 mb-4">
        MedicalTranslate
      </h1>
      <p className="text-lg text-gray-700">
        Hệ thống dịch thuật PDF Y khoa Anh - Việt
      </p>
      <div className="mt-8 p-4 bg-white rounded-lg shadow-md border border-gray-200">
        <p className="text-sm font-medium text-gray-500">Trạng thái API:</p>
        <p className={`font-bold mt-1 ${statusColor}`}>{apiMessage}</p>
      </div>
    </main>
  );
}