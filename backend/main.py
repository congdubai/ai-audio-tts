import os
import shutil
import uuid
import asyncio
import json
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from tts_service import TTSEngine, OUTPUTS_DIR
from video_service import VideoDubbingService, VIDEO_OUTPUTS_DIR, VIDEO_UPLOADS_DIR
from db import init_db, add_history_entry, get_history, delete_history_entry, add_video_history_entry, get_video_history
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
    title="Vietnamese TTS & Multi-Video Processing API (Kokoro - Ngọc Huyền)",
    description="API chuyển đổi văn bản thành giọng nói & lồng tiếng / ghép / xóa âm video tiếng Việt",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"[!] Validation error (422) on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

@app.get("/api/health")
async def health_check():
    engine = TTSEngine.get_instance()
    return {
        "status": "healthy",
        "model_ready": engine.is_ready,
        "device": engine.device,
        "model": "Kokoro Vietnamese TTS (dinhthuan/kokoro-vi-ngoc-huyen)",
        "voice": "Ngọc Huyền (Vietnamese)",
        "features": ["text-to-speech", "video-dubbing", "multi-video-concat", "video-audio-merge", "strip-audio", "background-music"]
    }

# ==================== TTS Endpoints ====================

@app.post("/api/tts/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(req: SynthesizeRequest):
    try:
        engine = TTSEngine.get_instance()
        result = engine.synthesize(text=req.text, speed=req.speed)

        # Save to DB history
        try:
            add_history_entry(
                item_id=result["id"],
                text=result["text"],
                speed=result["speed"],
                duration=result["duration"],
                phonemes=result["phonemes"],
                filename=result["filename"],
                file_size=result["file_size"]
            )
        except Exception as e:
            print(f"[!] Warning: Unable to save to history DB: {e}")

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

@app.post("/api/tts/synthesize-stream")
async def synthesize_speech_stream(req: SynthesizeRequest):
    async def event_generator():
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def progress_cb(current: int, total: int, chunk_text: str):
            pct = int((current / total) * 85)
            snippet = chunk_text[:45] + "..." if len(chunk_text) > 45 else chunk_text
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "percent": pct,
                    "message": f"Đang đọc đoạn {current}/{total}...",
                    "chunk": snippet
                }
            )

        def run_synth():
            engine = TTSEngine.get_instance()
            return engine.synthesize(text=req.text, speed=req.speed, progress_callback=progress_cb)

        future = loop.run_in_executor(None, run_synth)

        while not future.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.08)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                pass

        while not queue.empty():
            msg = queue.get_nowait()
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

        try:
            result = await future
            yield f"data: {json.dumps({'type': 'progress', 'percent': 95, 'message': 'Đang ghép nối & chuẩn hóa âm thanh...'}, ensure_ascii=False)}\n\n"

            # Save to DB history
            try:
                add_history_entry(
                    item_id=result["id"],
                    text=result["text"],
                    speed=result["speed"],
                    duration=result["duration"],
                    phonemes=result["phonemes"],
                    filename=result["filename"],
                    file_size=result["file_size"]
                )
            except Exception as e:
                print(f"[!] Warning: Unable to save to history DB: {e}")

            response_data = SynthesizeResponse(
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
            ).model_dump()

            yield f"data: {json.dumps({'type': 'complete', 'percent': 100, 'result': response_data}, ensure_ascii=False)}\n\n"
        except Exception as err:
            yield f"data: {json.dumps({'type': 'error', 'message': str(err)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/tts/audio/{audio_id}")
async def stream_audio(audio_id: str):
    filename = f"{audio_id}.wav"
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
    filename = f"{audio_id}.wav"
    file_path = OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file âm thanh.")

    download_name = f"ngoc_huyen_{audio_id[:8]}.wav"
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
    )

@app.get("/api/tts/history")
async def list_history():
    db_items = get_history(limit=50)
    db_ids = {item["id"] for item in db_items}
    items = []

    for item in db_items:
        items.append({
            "id": item["id"],
            "text": item["text"],
            "speed": item["speed"],
            "duration": item["duration"],
            "phonemes": item.get("phonemes", ""),
            "filename": item["filename"],
            "file_size": item["file_size"],
            "audio_url": f"/api/tts/audio/{item['id']}",
            "download_url": f"/api/tts/download/{item['id']}",
            "created_at": item.get("created_at", "")
        })

    # Also check outputs folder for any wav file not in DB
    if OUTPUTS_DIR.exists():
        for wav_file in sorted(OUTPUTS_DIR.glob("*.wav"), key=lambda f: f.stat().st_mtime, reverse=True):
            audio_id = wav_file.stem
            if audio_id not in db_ids:
                size = wav_file.stat().st_size
                dur = round(size / (24000 * 2), 2)
                items.append({
                    "id": audio_id,
                    "text": f"File Audio TTS ({audio_id[:8]})",
                    "speed": 1.0,
                    "duration": dur,
                    "phonemes": "",
                    "filename": wav_file.name,
                    "file_size": size,
                    "audio_url": f"/api/tts/audio/{audio_id}",
                    "download_url": f"/api/tts/download/{audio_id}",
                    "created_at": ""
                })

    return items

@app.delete("/api/tts/history/{audio_id}")
async def delete_history(audio_id: str):
    file_path = OUTPUTS_DIR / f"{audio_id}.wav"
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass
    delete_history_entry(audio_id)
    return {"status": "success", "message": "Đã xóa bản ghi thành công."}

# ==================== Multi-Video Dubbing & Processing Endpoints ====================

@app.post("/api/video/dub")
async def dub_multiple_videos(
    videos: List[UploadFile] = File(...),
    audio_file: Optional[UploadFile] = File(None),
    audio_id: Optional[str] = Form(None),
    bgm_file: Optional[UploadFile] = File(None),
    bgm_volume: float = Form(0.2),
    remove_original_audio: bool = Form(True),
    duration_mode: str = Form("full_video")  # "full_video" | "match_voice" | "loop_voice"
):
    temp_paths: List[Path] = []
    temp_audio_path: Optional[Path] = None
    temp_bgm_path: Optional[Path] = None
    is_custom_uploaded_audio = False
    is_custom_uploaded_bgm = False

    try:
        if not videos or len(videos) == 0:
            raise HTTPException(status_code=400, detail="Vui lòng tải lên ít nhất 1 video.")

        # Save video uploads
        for idx, video in enumerate(videos):
            temp_filename = f"upload_{idx}_{uuid.uuid4()}_{video.filename}"
            temp_path = VIDEO_UPLOADS_DIR / temp_filename
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
            temp_paths.append(temp_path)

        # Handle Voice Audio input source
        if audio_file is not None and audio_file.filename:
            print(f"[*] Nhận file audio voice tải lên: {audio_file.filename}")
            temp_audio_name = f"upload_audio_{uuid.uuid4()}_{audio_file.filename}"
            temp_audio_path = VIDEO_UPLOADS_DIR / temp_audio_name
            with open(temp_audio_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)
            is_custom_uploaded_audio = True

        elif audio_id and audio_id.strip() and audio_id != "none":
            clean_audio_id = audio_id.strip()
            existing_audio = OUTPUTS_DIR / f"{clean_audio_id}.wav"
            if existing_audio.exists():
                print(f"[*] Sử dụng file audio từ lịch sử TTS: {clean_audio_id}.wav")
                temp_audio_path = existing_audio

        # Handle Background Music (BGM) input source
        if bgm_file is not None and bgm_file.filename:
            print(f"[*] Nhận file nhạc nền (BGM) tải lên: {bgm_file.filename} (volume={bgm_volume})")
            temp_bgm_name = f"upload_bgm_{uuid.uuid4()}_{bgm_file.filename}"
            temp_bgm_path = VIDEO_UPLOADS_DIR / temp_bgm_name
            with open(temp_bgm_path, "wb") as buffer:
                shutil.copyfileobj(bgm_file.file, buffer)
            is_custom_uploaded_bgm = True

        # Process video (dub, merge, bgm, strip audio)
        result = VideoDubbingService.process_video_dubbing(
            video_paths=temp_paths,
            audio_file_path=temp_audio_path,
            bgm_file_path=temp_bgm_path,
            bgm_volume=bgm_volume,
            remove_original_audio=remove_original_audio,
            duration_mode=duration_mode
        )

        # Cleanup video temp files
        for tp in temp_paths:
            if tp.exists():
                try:
                    os.remove(tp)
                except Exception:
                    pass

        # Cleanup custom uploaded voice audio temp file
        if is_custom_uploaded_audio and temp_audio_path and temp_audio_path.exists():
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass

        # Cleanup custom uploaded bgm temp file
        if is_custom_uploaded_bgm and temp_bgm_path and temp_bgm_path.exists():
            try:
                os.remove(temp_bgm_path)
            except Exception:
                pass

        return {
            "id": result["id"],
            "has_voice": result["has_voice"],
            "has_bgm": result["has_bgm"],
            "bgm_volume": result["bgm_volume"],
            "duration": result["video_duration"],
            "video_url": f"/api/video/stream/{result['id']}",
            "download_url": f"/api/video/download/{result['id']}",
            "file_size": result["file_size"],
            "video_count": result.get("video_count", len(videos)),
            "remove_original_audio": result["remove_original_audio"]
        }

    except Exception as e:
        # Cleanup on error
        for tp in temp_paths:
            if tp.exists():
                try:
                    os.remove(tp)
                except Exception:
                    pass
        if is_custom_uploaded_audio and temp_audio_path and temp_audio_path.exists():
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass
        if is_custom_uploaded_bgm and temp_bgm_path and temp_bgm_path.exists():
            try:
                os.remove(temp_bgm_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý video: {str(e)}"
        )

@app.get("/api/video/stream/{video_id}")
async def stream_video(video_id: str):
    filename = f"dubbed_{video_id}.mp4"
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
    filename = f"dubbed_{video_id}.mp4"
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
    return []

@app.delete("/api/video/history/{video_id}")
async def delete_video_history(video_id: str):
    file_path = VIDEO_OUTPUTS_DIR / f"dubbed_{video_id}.mp4"
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass

    return {"status": "success", "message": "Đã xóa video thành công."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
