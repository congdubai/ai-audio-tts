import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from tts_service import TTSEngine, OUTPUTS_DIR
from db import init_db, add_history_entry, get_history, get_history_by_id, delete_history_entry
from models import SynthesizeRequest, SynthesizeResponse, HistoryItem

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and pre-warm model
    init_db()
    print("[*] Server starting up, warming up model...")
    try:
        engine = TTSEngine.get_instance()
        engine.initialize()
    except Exception as e:
        print(f"[!] Warning: Model preload deferred or failed: {e}")
    yield
    # Shutdown
    print("[*] Server shutting down...")

app = FastAPI(
    title="Vietnamese TTS API (Kokoro - Ngọc Huyền)",
    description="API chuyển đổi văn bản thành giọng nói tiếng Việt sử dụng Model Kokoro finetuned Ngọc Huyền",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    engine = TTSEngine.get_instance()
    return {
        "status": "healthy",
        "model_ready": engine.is_ready,
        "device": engine.device,
        "voice": "Ngọc Huyền (Vietnamese)"
    }

@app.post("/api/tts/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(req: SynthesizeRequest):
    try:
        engine = TTSEngine.get_instance()
        result = engine.synthesize(text=req.text, speed=req.speed)

        # Save record to history database
        add_history_entry(
            item_id=result["id"],
            text=result["text"],
            speed=result["speed"],
            duration=result["duration"],
            phonemes=result["phonemes"],
            filename=result["filename"],
            file_size=result["file_size"]
        )

        return SynthesizeResponse(
            id=result["id"],
            text=result["text"],
            speed=result["speed"],
            duration=result["duration"],
            sample_rate=result["sample_rate"],
            phonemes=result["phonemes"],
            audio_url=f"/api/tts/audio/{result['id']}",
            download_url=f"/api/tts/download/{result['id']}",
            file_size=result["file_size"],
            elapsed_time=result["elapsed_time"],
            device=result["device"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý tổng hợp giọng nói: {str(e)}"
        )

@app.get("/api/tts/audio/{audio_id}")
async def stream_audio(audio_id: str):
    record = get_history_by_id(audio_id)
    filename = record["filename"] if record else f"{audio_id}.wav"
    file_path = OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file âm thanh.")

    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=filename
    )

@app.get("/api/tts/download/{audio_id}")
async def download_audio(audio_id: str):
    record = get_history_by_id(audio_id)
    filename = record["filename"] if record else f"{audio_id}.wav"
    file_path = OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file âm thanh.")

    download_name = f"ngoc_huyen_{audio_id[:8]}.wav"
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
    )

@app.get("/api/tts/history", response_model=list[HistoryItem])
async def list_history():
    records = get_history(limit=50)
    history = []
    for r in records:
        history.append(HistoryItem(
            id=r["id"],
            text=r["text"],
            speed=r["speed"],
            duration=r["duration"],
            phonemes=r["phonemes"],
            filename=r["filename"],
            file_size=r["file_size"],
            created_at=r["created_at"],
            audio_url=f"/api/tts/audio/{r['id']}",
            download_url=f"/api/tts/download/{r['id']}"
        ))
    return history

@app.delete("/api/tts/history/{audio_id}")
async def delete_history(audio_id: str):
    record = get_history_by_id(audio_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bản ghi không tồn tại.")
    
    # Remove file from disk
    file_path = OUTPUTS_DIR / record["filename"]
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass

    # Remove from database
    delete_history_entry(audio_id)
    return {"status": "success", "message": "Đã xóa bản ghi thành công."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
