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
        """
        1. Synthesize Vietnamese TTS audio using Kokoro model.
        2. If multiple videos: Concatenate all clips seamlessly.
        3. Merge video + TTS audio according to duration_mode.
        """
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

        # Build audio filter & duration flags
        # If duration_mode == "full_video": pad audio with silence so full video plays
        # If duration_mode == "match_voice": cut video with -shortest
        # If duration_mode == "loop_voice": loop audio until video ends
        
        is_cut_to_voice = (duration_mode == "match_voice")
        is_loop_voice = (duration_mode == "loop_voice")

        if len(video_paths) == 1:
            video_path = video_paths[0]
            
            if is_cut_to_voice:
                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    str(output_filepath)
                ]
            elif is_loop_voice:
                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-stream_loop", "-1",
                    "-i", str(audio_file_path),
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    str(output_filepath)
                ]
            else:
                # Default "full_video": Keep full video length, pad audio with silence if needed
                cmd = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-af", "apad",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    str(output_filepath)
                ]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                # Re-encode fallback
                cmd_reencode = [
                    ffmpeg_bin, "-y",
                    "-i", str(video_path),
                    "-i", str(audio_file_path),
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-af", "apad" if not is_cut_to_voice else "anull",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    *("-shortest",),
                    str(output_filepath)
                ]
                result_reencode = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result_reencode.returncode != 0:
                    raise RuntimeError(f"FFmpeg error: {result_reencode.stderr}")

        else:
            # Multi-video concatenation: Always normalize frame size, rate, and concat robustly
            inputs = []
            filter_parts = []
            for idx, vp in enumerate(video_paths):
                inputs.extend(["-i", str(vp)])
                filter_parts.append(
                    f"[{idx}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{idx}];"
                )

            concat_streams = "".join([f"[v{i}]" for i in range(len(video_paths))])
            filter_str = "".join(filter_parts) + f"{concat_streams}concat=n={len(video_paths)}:v=1:a=0[v_out]"

            if is_cut_to_voice:
                cmd_complex = [
                    ffmpeg_bin, "-y",
                    *inputs,
                    "-i", str(audio_file_path),
                    "-filter_complex", filter_str,
                    "-map", "[v_out]",
                    "-map", f"{len(video_paths)}:a:0",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]
            elif is_loop_voice:
                cmd_complex = [
                    ffmpeg_bin, "-y",
                    *inputs,
                    "-stream_loop", "-1",
                    "-i", str(audio_file_path),
                    "-filter_complex", filter_str,
                    "-map", "[v_out]",
                    "-map", f"{len(video_paths)}:a:0",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]
            else:
                # Default "full_video": Keep all videos completely (9m + 40s = 9m40s)
                cmd_complex = [
                    ffmpeg_bin, "-y",
                    *inputs,
                    "-i", str(audio_file_path),
                    "-filter_complex", filter_str,
                    "-map", "[v_out]",
                    "-map", f"{len(video_paths)}:a:0",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-af", "apad",
                    "-shortest",
                    str(output_filepath)
                ]

            result_complex = subprocess.run(cmd_complex, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result_complex.returncode != 0:
                raise RuntimeError(f"FFmpeg multi-video complex error: {result_complex.stderr}")

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
