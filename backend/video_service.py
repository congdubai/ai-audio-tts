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
        remove_original_audio: bool = True
    ) -> Dict[str, Any]:
        """
        1. Synthesize Vietnamese TTS audio using Kokoro model.
        2. If multiple videos: Concatenate them sequentially.
        3. Remove original audio and merge with generated TTS voice.
        4. Save and return output MP4.
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

        if len(video_paths) == 1:
            # Single video processing
            video_path = video_paths[0]
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
                # Fallback re-encode if stream copy fails
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
                    raise RuntimeError(f"FFmpeg single video error: {result_reencode.stderr}")
        else:
            # Multi-video concatenation & dubbing
            # Create a concat list file
            concat_list_file = VIDEO_UPLOADS_DIR / f"concat_{video_id}.txt"
            with open(concat_list_file, "w", encoding="utf-8") as f:
                for vp in video_paths:
                    escaped_path = str(vp.resolve()).replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")

            # Try demuxer concat with stream copy first
            cmd_concat = [
                ffmpeg_bin,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_file),
                "-i", str(audio_file_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(output_filepath)
            ]
            result_concat = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result_concat.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                # If codecs differ, use filter_complex to normalize and concatenate seamlessly
                inputs = []
                filter_parts = []
                for idx, vp in enumerate(video_paths):
                    inputs.extend(["-i", str(vp)])
                    filter_parts.append(f"[{idx}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v{idx}];")

                concat_streams = "".join([f"[v{i}]" for i in range(len(video_paths))])
                filter_str = "".join(filter_parts) + f"{concat_streams}concat=n={len(video_paths)}:v=1:a=0[v_out]"

                cmd_complex = [
                    ffmpeg_bin,
                    "-y",
                    *inputs,
                    "-i", str(audio_file_path),
                    "-filter_complex", filter_str,
                    "-map", "[v_out]",
                    "-map", f"{len(video_paths)}:a:0",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    str(output_filepath)
                ]
                result_complex = subprocess.run(cmd_complex, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result_complex.returncode != 0:
                    raise RuntimeError(f"FFmpeg multi-video complex error: {result_complex.stderr}")

            # Cleanup concat list file
            if concat_list_file.exists():
                try:
                    os.remove(concat_list_file)
                except Exception:
                    pass

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
            "video_count": len(video_paths)
        }
