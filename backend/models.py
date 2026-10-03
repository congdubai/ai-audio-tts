from pydantic import BaseModel, Field
from typing import Optional, List

class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000, description="Văn bản tiếng Việt cần chuyển đổi")
    speed: Optional[float] = Field(1.0, ge=0.1, le=5.0, description="Tốc độ giọng đọc (0.1 đến 5.0)")
    pause_ms: Optional[int] = Field(150, ge=0, le=2000, description="Thời gian tạm ngắt giữa các câu (ms)")

class SynthesizeResponse(BaseModel):
    id: str
    text: str
    speed: float
    duration: float
    sample_rate: int
    phonemes: Optional[str] = None
    audio_url: str
    download_url: str
    file_size: int
    elapsed_time: float
    device: str

class HistoryItem(BaseModel):
    id: str
    text: str
    speed: float
    duration: float
    phonemes: Optional[str] = None
    filename: str
    file_size: int
    created_at: str
    audio_url: str
    download_url: str

class ZhihuSearchRequest(BaseModel):
    genres: List[str] = Field(..., min_length=1, max_length=20, description="Thể loại / từ khoá tiếng Việt")
    scrolls: int = Field(4, ge=0, le=30, description="Số lần cuộn trang kết quả")
    translate: bool = Field(True, description="Dịch tiêu đề & trích đoạn sang tiếng Việt")
    model: Optional[str] = Field(None, description="Model Ollama, mặc định qwen2.5:7b")
    headless: bool = Field(False, description="Chạy trình duyệt ẩn")
    wait_captcha: bool = Field(False, description="Chờ người dùng tự giải captcha thay vì dừng")
