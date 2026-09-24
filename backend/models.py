from pydantic import BaseModel, Field
from typing import Optional, List

class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Văn bản tiếng Việt cần chuyển đổi")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Tốc độ giọng đọc (0.5 đến 2.0)")

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
