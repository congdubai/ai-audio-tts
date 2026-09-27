import os
import re
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import imageio_ffmpeg

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
            print(f"[!] Warning: Khong the lay duration: {e}")
        return 0.0

    @classmethod
    def process_video_dubbing(
        cls,
        video_paths: List[Path],
        audio_file_path: Optional[Path] = None,
        remove_original_audio: bool = True,
        duration_mode: str = "full_video"  # "full_video" | "match_voice" | "loop_voice"
    ) -> Dict[str, Any]:
        if not video_paths:
            raise ValueError("Cần ít nhất một file video để xử lý.")

        video_id = str(uuid.uuid4())
        output_filename = f"dubbed_{video_id}.mp4"
        output_filepath = VIDEO_OUTPUTS_DIR / output_filename
        ffmpeg_bin = cls.get_ffmpeg_bin()

        has_audio = audio_file_path is not None and audio_file_path.exists()
        voice_dur = cls.get_video_duration(audio_file_path) if has_audio else 0.0

        print(f"[*] Bat dau xu ly video ({len(video_paths)} clip). Audio: {'Co (' + str(voice_dur) + 's)' if has_audio else 'Khong'}, Xoa am goc: {remove_original_audio}, Mode: {duration_mode}")

        # SINGLE VIDEO CASE
        if len(video_paths) == 1:
            video_path = video_paths[0]
            video_dur = cls.get_video_duration(video_path)

            if not has_audio:
                # Scenario A: No new audio provided
                if remove_original_audio:
                    print("[*] Stream copy: Xoa am thanh goc khoi video...")
                    cmd = [
                        ffmpeg_bin, "-y",
                        "-threads", "0",
                        "-i", str(video_path),
                        "-map", "0:v:0",
                        "-an",
                        "-c:v", "copy",
                        str(output_filepath)
                    ]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                        cmd_fallback = [
                            ffmpeg_bin, "-y",
                            "-threads", "0",
                            "-i", str(video_path),
                            "-an",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            str(output_filepath)
                        ]
                        subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                else:
                    print("[*] Stream copy video (giu nguyen am goc)...")
                    cmd = [
                        ffmpeg_bin, "-y",
                        "-threads", "0",
                        "-i", str(video_path),
                        "-c", "copy",
                        str(output_filepath)
                    ]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
                        cmd_fallback = [
                            ffmpeg_bin, "-y",
                            "-threads", "0",
                            "-i", str(video_path),
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k",
                            str(output_filepath)
                        ]
                        subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

            else:
                # Scenario B: New audio provided
                if remove_original_audio:
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
                    else: # full_video
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

                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
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
                        subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

                else:
                    # Keep original audio & mix with new audio
                    print("[*] Tron am thanh goc video voi audio moi (amix)...")
                    cmd_mix = [
                        ffmpeg_bin, "-y",
                        "-threads", "0",
                        "-i", str(video_path),
                        "-i", str(audio_file_path),
                        "-filter_complex", "[0:a:0][1:a:0]amix=inputs=2:duration=first[aout]",
                        "-map", "0:v:0",
                        "-map", "[aout]",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k",
                        *(["-t", str(video_dur)] if video_dur > 0 else []),
                        str(output_filepath)
                    ]
                    subprocess.run(cmd_mix, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        # MULTI-VIDEO CONCATENATION CASE
        else:
            num_vids = len(video_paths)
            print(f"[*] Dang ghep noi {num_vids} video...")
            inputs = []
            filter_parts = []

            for idx, vp in enumerate(video_paths):
                inputs.extend(["-i", str(vp)])
                filter_parts.append(
                    f"[{idx}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-ih)/2:(oh-ih)/2,setsar=1,fps=30[v{idx}];"
                )

            concat_v = "".join([f"[v{i}]" for i in range(num_vids)])

            if not has_audio:
                filter_parts.append(f"{concat_v}concat=n={num_vids}:v=1:a=0[vout]")
                full_filter = "".join(filter_parts)

                cmd_complex = [
                    ffmpeg_bin, "-y",
                    "-threads", "0",
                    *inputs,
                    "-filter_complex", full_filter,
                    "-map", "[vout]",
                    "-an",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(output_filepath)
                ]
                subprocess.run(cmd_complex, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

            else:
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
                subprocess.run(cmd_complex, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        if not output_filepath.exists() or output_filepath.stat().st_size == 0:
            raise RuntimeError("Tạo file video thất bại.")

        file_size = output_filepath.stat().st_size
        final_duration = cls.get_video_duration(output_filepath)
        print(f"[OK] Xu ly video thanh cong! File: {output_filename} ({round(file_size / (1024*1024), 2)} MB, {final_duration:.2f}s)")

        return {
            "id": video_id,
            "has_audio": has_audio,
            "audio_duration": voice_dur,
            "filename": output_filename,
            "file_size": file_size,
            "video_duration": final_duration,
            "video_count": len(video_paths),
            "duration_mode": duration_mode,
            "remove_original_audio": remove_original_audio
        }
