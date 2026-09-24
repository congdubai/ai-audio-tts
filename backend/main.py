import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from tts_service import TTSEngine, OUTPUTS_DIR
from video_service import VideoDubbingService, VIDEO_OUTPUTS_DIR, VIDEO_UPLOADS_DIR
from db import (
    init_db,
    add_history_entry,
    get_history,
    get_history_by_id,
    delete_history_entry,
    add_video_history_entry,
    get_video_history,
    get_video_history_by_id,
    delete_video_history_entry
)
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
    title="Vietnamese TTS & Video Dubbing API (Kokoro - Ngọc Huyền)",
    description="API chuyển đổi văn bản thành giọng nói & lồng tiếng video tiếng Việt sử dụng Model Kokoro finetuned Ngọc Huyền",
    version="1.1.0",
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
        "voice": "Ngọc Huyền (Vietnamese)",
        "features": ["text-to-speech", "video-dubbing"]
    }

# ==================== TTS Endpoints ====================

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
    
    file_path = OUTPUTS_DIR / record["filename"]
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass

    delete_history_entry(audio_id)
    return {"status": "success", "message": "Đã xóa bản ghi thành công."}

# ==================== Video Dubbing Endpoints ====================

@app.post("/api/video/dub")
async def dub_video(
    video: UploadFile = File(...),
    text: str = Form(...),
    speed: float = Form(1.0),
    remove_original_audio: bool = Form(True)
):
    try:
        clean_text = text.strip()
        if not clean_text:
            raise HTTPException(status_code=400, detail="Văn bản lồng tiếng không được để trống.")

        # Save uploaded video temporarily
        temp_video_filename = f"upload_{uuid.uuid4()}_{video.filename}"
        temp_video_path = VIDEO_UPLOADS_DIR / temp_video_filename
        
        with open(temp_video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        # Process dubbing
        result = VideoDubbingService.process_video_dubbing(
            video_path=temp_video_path,
            text=clean_text,
            speed=speed,
            remove_original_audio=remove_original_audio
        )

        # Cleanup uploaded raw video
        if temp_video_path.exists():
            try:
                os.remove(temp_video_path)
            except Exception:
                pass

        # Save to video history
        add_video_history_entry(
            item_id=result["id"],
            text=result["text"],
            speed=result["speed"],
            duration=result["audio_duration"],
            filename=result["filename"],
            file_size=result["file_size"]
        )

        return {
            "id": result["id"],
            "text": result["text"],
            "speed": result["speed"],
            "duration": result["audio_duration"],
            "video_url": f"/api/video/stream/{result['id']}",
            "download_url": f"/api/video/download/{result['id']}",
            "file_size": result["file_size"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý lồng tiếng video: {str(e)}"
        )

@app.get("/api/video/stream/{video_id}")
async def stream_video(video_id: str):
    record = get_video_history_by_id(video_id)
    filename = record["filename"] if record else f"dubbed_{video_id}.mp4"
    file_path = VIDEO_OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file video.")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename
    )

@app.get("/api/video/download/{video_id}")
async def download_video(video_id: str):
    record = get_video_history_by_id(video_id)
    filename = record["filename"] if record else f"dubbed_{video_id}.mp4"
    file_path = VIDEO_OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file video.")

    download_name = f"dubbed_ngoc_huyen_{video_id[:8]}.mp4"
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
    )

@app.get("/api/video/history")
async def list_video_history():
    records = get_video_history(limit=50)
    history = []
    for r in records:
        history.append({
            "id": r["id"],
            "text": r["text"],
            "speed": r["speed"],
            "duration": r["duration"],
            "filename": r["filename"],
            "file_size": r["file_size"],
            "created_at": r["created_at"],
            "video_url": f"/api/video/stream/{r['id']}",
            "download_url": f"/api/video/download/{r['id']}"
        })
    return history

@app.delete("/api/video/history/{video_id}")
async def delete_video_history(video_id: str):
    record = get_video_history_by_id(video_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bản ghi video không tồn tại.")
    
    file_path = VIDEO_OUTPUTS_DIR / record["filename"]
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass

    delete_video_history_entry(video_id)
    return {"status": "success", "message": "Đã xóa video thành công."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
