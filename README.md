# 🎙️ Kokoro Vietnamese TTS (React + FastAPI)

Ứng dụng web chuyển đổi văn bản thành giọng nói (Text-to-Speech) tiếng Việt chất lượng cao sử dụng model **Kokoro-82M (Giọng Ngọc Huyền)** với giao diện **React** hiện đại và backend **FastAPI**.

---

## 🌟 Tính Năng Chính
- **Giọng đọc tiếng Việt tự nhiên**: Sử dụng finetuned Kokoro TTS với voicepack Ngọc Huyền & `vig2p`.
- **Giao diện hiện đại**: Thiết kế Dark Mode Glassmorphism, hiển thị trực quan sóng âm (Equalizer Bars).
- **Tùy chỉnh tốc độ**: Điều chỉnh tốc độ đọc linh hoạt từ `0.5x` đến `2.0x`.
- **Tải file âm thanh**: Tải trực tiếp file âm thanh chuẩn `.wav` 24kHz về máy tính.
- **Lịch sử & Caching**: Lưu trữ các câu đã tạo, phát lại và quản lý lịch sử thuận tiện.

---

## 🚀 Hướng Dẫn Khởi Động Nhanh (1-Click)

Chỉ cần nhấp đúp chuột vào file **`start_app.bat`** tại thư mục gốc của dự án:
- **Frontend**: http://localhost:5173
- **Backend API**: http://127.0.0.1:8000/docs

---

## 🛠️ Cài Đặt Thủ Công

### 1. Cài đặt Backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Cài đặt dependencies:
pip install -r requirements.txt
pip install torch --extra-index-url https://download.pytorch.org/whl/cu121
# Chạy backend:
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Cài đặt Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

---

## 📂 Cấu Trúc Dự Án
```text
├── backend/                  # FastAPI Backend API & SQLite History
├── frontend/                 # React (Vite) User Interface
├── kokoro-vi-ngoc-huyen/     # Model Kokoro Vietnamese Voice Engine
├── start_app.bat             # Script chạy nhanh 1-Click
└── README.md
```
