import os
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import imageio_ffmpeg
from tts_service import TTSEngine

VIDEO_OUTPUTS_DIR = Path(__file__).parent / "video_outputs"
VIDEO_UPLOADS_DIR = Path(__file__).parent / "video_uploads"
VIDEO_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

class VideoDubbingService:
    @staticmethod
    def get_ffmpeg_bin() -> str:
        return imageio_ffmpeg.get_ffmpeg_exe()

    @classmethod
    def process_video_dubbing(
        cls,
        video_path: Path,
        text: str,
        speed: float = 1.0,
        remove_original_audio: bool = True
    ) -> Dict[str, Any]:
        """
        1. Synthesize Vietnamese TTS audio using Kokoro model.
        2. Remove original audio from video and merge with generated TTS voice.
        3. Save and return output MP4.
        """
        # Step 1: Synthesize voice
        engine = TTSEngine.get_instance()
        tts_result = engine.synthesize(text=text, speed=speed)
        audio_file_path = engine.get_audio_path(tts_result["filename"])

        if not audio_file_path or not audio_file_path.exists():
            raise RuntimeError("Không thể tìm thấy file âm thanh đã sinh.")

        video_id = str(uuid.uuid4())
        output_filename = f"dubbed_{video_id}.mp4"
        output_filepath = VIDEO_OUTPUTS_DIR / output_filename

        ffmpeg_bin = cls.get_ffmpeg_bin()

        # Step 2: Merge video with AI voice
        # We replace the audio track completely with AI voice
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_file_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_filepath)
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            # Fallback if video codec copy fails (re-encode video)
            cmd_reencode = [
                ffmpeg_bin,
                "-y",
                "-i", str(video_path),
                "-i", str(audio_file_path),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(output_filepath)
            ]
            result_reencode = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result_reencode.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result_reencode.stderr}")

        if not output_filepath.exists() or output_filepath.stat().st_size == 0:
            raise RuntimeError("Tạo file video lồng tiếng thất bại.")

        file_size = output_filepath.stat().st_size

        return {
            "id": video_id,
            "text": text,
            "speed": speed,
            "audio_duration": tts_result["duration"],
            "filename": output_filename,
            "file_size": file_size,
            "audio_id": tts_result["id"]
        }
