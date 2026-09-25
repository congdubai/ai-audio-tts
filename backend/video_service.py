import os
import re
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
    def get_video_duration(cls, video_path: Path) -> float:
        try:
            ffmpeg_bin = cls.get_ffmpeg_bin()
            proc = subprocess.run(
                [ffmpeg_bin, "-i", str(video_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
            if match:
                h, m, s = match.groups()
                return float(h) * 3600 + float(m) * 60 + float(s)
        except Exception as e:
            print(f"[!] Warning: Khong the lay duration video: {e}")
        return 0.0

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

        print(f"[*] Bat dau xu ly long tieng cho {len(video_paths)} video. Do dai van ban: {len(text)} ky tu...")
        print("[*] Dang tao giong noi bang Kokoro TTS...")

        # Step 1: Synthesize voice
        engine = TTSEngine.get_instance()
        tts_result = engine.synthesize(text=text, speed=speed)
        audio_file_path = engine.get_audio_path(tts_result["filename"])

        if not audio_file_path or not audio_file_path.exists():
            raise RuntimeError("Không thể tìm thấy file âm thanh đã sinh.")

        voice_dur = float(tts_result["duration"])
        print(f"[*] Giong noi da tao xong ({voice_dur}s). Dang xu ly video bang FFmpeg...")

        video_id = str(uuid.uuid4())
        output_filename = f"dubbed_{video_id}.mp4"
        output_filepath = VIDEO_OUTPUTS_DIR / output_filename
        ffmpeg_bin = cls.get_ffmpeg_bin()

        if len(video_paths) == 1:
            video_path = video_paths[0]
            video_dur = cls.get_video_duration(video_path)
            print(f"[*] Thong tin video: Do dai video = {video_dur:.2f}s, Do dai giong doc = {voice_dur:.2f}s")
            
            if duration_mode == "match_voice":
                target_dur = voice_dur if voice_dur > 0 else (video_dur or 10)
                cmd = [
                    ffmpeg_bin, "-y",
                    "-threads", "0",
                    "-ss", "0",
                    "-t", str(target_dur),
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    str(output_filepath)
                ]
            elif duration_mode == "loop_voice":
                cmd = [
                    ffmpeg_bin, "-y",
                    "-threads", "0",
                    "-i", str(video_path),
                    "-stream_loop", "-1",
                    "-i", str(audio_file_path),
                    *(["-t", str(video_dur)] if video_dur > 0 else []),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    str(output_filepath)
                ]
            else:
                # Default "full_video": Keep entire video length, stream copy video (instant ~2s)
                cmd = [
                    ffmpeg_bin, "-y",
                    "-threads", "0",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    *(["-t", str(video_dur)] if video_dur > 0 else []),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    str(output_filepath)
                ]

            print("[*] Dang chay FFmpeg stream copy (cuc nhanh, giu nguyen 100% chat luong goc)...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                print("[*] Stream copy khong phu hop voi codec, chuyen sang che do encode ultrafast...")
                time_arg = ["-t", str(video_dur)] if (video_dur > 0 and duration_mode == "full_video") else (["-t", str(voice_dur)] if duration_mode == "match_voice" else [])
                cmd_fallback = [
                    ffmpeg_bin, "-y",
                    "-threads", "0",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    *time_arg,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    str(output_filepath)
                ]
                result_fallback = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result_fallback.returncode != 0:
                    raise RuntimeError(f"FFmpeg error: {result_fallback.stderr}")

        else:
            print(f"[*] Dang ghep noi {len(video_paths)} video va ma hoa lai (ultrafast)...")
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

            if duration_mode == "loop_voice":
                filter_parts.append(f"[{num_vids}:a:0]aloop=loop=-1:size=2147483647[aout]")
            elif duration_mode == "match_voice":
                filter_parts.append(f"[{num_vids}:a:0]anull[aout]")
            else:
                filter_parts.append(f"[{num_vids}:a:0]apad[aout]")

            full_filter = "".join(filter_parts)

            cmd_complex = [
                ffmpeg_bin, "-y",
                "-threads", "0",
                *inputs,
                "-i", str(audio_file_path),
                "-filter_complex", full_filter,
                "-map", "[vout]",
                "-map", "[aout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
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
        print(f"[OK] Xu ly video thanh cong! File luu tai: {output_filename} ({round(file_size / (1024*1024), 2)} MB)")

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
