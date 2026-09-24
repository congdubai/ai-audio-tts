import os
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
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
        video_paths: List[Path],
        text: str,
        speed: float = 1.0,
        remove_original_audio: bool = True,
        duration_mode: str = "full_video"  # "full_video" | "match_voice" | "loop_voice"
    ) -> Dict[str, Any]:
        if not video_paths:
            raise ValueError("Cần ít nhất một file video để xử lý.")

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

        if len(video_paths) == 1:
            video_path = video_paths[0]
            
            if duration_mode == "match_voice":
                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]
            elif duration_mode == "loop_voice":
                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-stream_loop", "-1",
                    "-i", str(audio_file_path),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]
            else:
                # Default "full_video": Keep entire video length
                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-filter_complex", "[1:a:0]apad[aout]",
                    "-map", "0:v:0",
                    "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                # Fallback with video re-encode
                cmd_fallback = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-filter_complex", "[1:a:0]apad[aout]" if duration_mode == "full_video" else "[1:a:0]anull[aout]",
                    "-map", "0:v:0",
                    "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]
                result_fallback = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result_fallback.returncode != 0:
                    raise RuntimeError(f"FFmpeg error: {result_fallback.stderr}")

        else:
            # Multi-video concatenation: Scale, pad, setsar, and concat in filter_complex
            num_vids = len(video_paths)
            inputs = []
            filter_parts = []
            
            for idx, vp in enumerate(video_paths):
                inputs.extend(["-i", str(vp)])
                filter_parts.append(
                    f"[{idx}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{idx}];"
                )

            concat_v = "".join([f"[v{i}]" for i in range(num_vids)])
            filter_parts.append(f"{concat_v}concat=n={num_vids}:v=1:a=0[vout];")

            # Audio handling in same filter_complex
            if duration_mode == "loop_voice":
                filter_parts.append(f"[{num_vids}:a:0]aloop=loop=-1:size=2147483647[aout]")
            elif duration_mode == "match_voice":
                filter_parts.append(f"[{num_vids}:a:0]anull[aout]")
            else:
                # Default "full_video"
                filter_parts.append(f"[{num_vids}:a:0]apad[aout]")

            full_filter = "".join(filter_parts)

            cmd_complex = [
                ffmpeg_bin, "-y",
                *inputs,
                "-i", str(audio_file_path),
                "-filter_complex", full_filter,
                "-map", "[vout]",
                "-map", "[aout]",
                "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(output_filepath)
            ]

            result_complex = subprocess.run(cmd_complex, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result_complex.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                raise RuntimeError(f"FFmpeg multi-video error: {result_complex.stderr}")

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
            "audio_id": tts_result["id"],
            "video_count": len(video_paths),
            "duration_mode": duration_mode
        }
