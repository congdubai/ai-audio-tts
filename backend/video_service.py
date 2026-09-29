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
        audio_file_paths: List[Path] = [],
        bgm_file_path: Optional[Path] = None,
        bgm_volume: float = 0.2,
        remove_original_audio: bool = True,
        duration_mode: str = "full_video",  # "full_video" | "match_voice" | "loop_voice"
        aspect_ratio: str = "9:16",  # "9:16" (TikTok 1080x1920) | "16:9" | "1:1"
        fit_mode: str = "blur_bg"  # "blur_bg" | "pad_black"
    ) -> Dict[str, Any]:
        if not video_paths:
            raise ValueError("Cần ít nhất một file video để xử lý.")

        video_id = str(uuid.uuid4())
        output_filename = f"dubbed_{video_id}.mp4"
        output_filepath = VIDEO_OUTPUTS_DIR / output_filename
        ffmpeg_bin = cls.get_ffmpeg_bin()

        valid_audio_paths = [ap for ap in audio_file_paths if ap and ap.exists()]
        has_voice = len(valid_audio_paths) > 0
        has_bgm = bgm_file_path is not None and bgm_file_path.exists()

        voice_dur = sum(cls.get_video_duration(ap) for ap in valid_audio_paths) if has_voice else 0.0
        bgm_dur = cls.get_video_duration(bgm_file_path) if has_bgm else 0.0

        num_vids = len(video_paths)
        inputs = []
        for vp in video_paths:
            inputs.extend(["-i", str(vp)])

        voice_indices = []
        if has_voice:
            for ap in valid_audio_paths:
                voice_indices.append(len(inputs) // 2)
                inputs.extend(["-i", str(ap)])

        bgm_idx = None
        if has_bgm:
            bgm_idx = len(inputs) // 2
            inputs.extend(["-i", str(bgm_file_path)])

        video_dur = sum(cls.get_video_duration(vp) for vp in video_paths)

        # Determine target resolution based on aspect_ratio
        if aspect_ratio == "9:16":
            target_w, target_h = 1080, 1920
        elif aspect_ratio == "1:1":
            target_w, target_h = 1080, 1080
        else:
            target_w, target_h = 1920, 1080

        # Determine target duration
        if duration_mode == "match_voice" and has_voice and voice_dur > 0:
            target_dur = voice_dur
        else:
            target_dur = video_dur

        filter_parts = []
        audio_mix_streams = []

        print(f"[*] Processing Video ({num_vids} clips). Aspect ratio: {aspect_ratio} ({target_w}x{target_h}, fit={fit_mode}). Voice total: {voice_dur:.2f}s, BGM: {'Yes (' + str(bgm_dur) + 's)' if has_bgm else 'No'}")

        # Construct Video Scaling Filter
        if num_vids == 1:
            if fit_mode == "blur_bg":
                filter_parts.append(
                    f"[0:v:0]split[bg0][fg0];"
                    f"[bg0]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=20:5[bgblur0];"
                    f"[fg0]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fgscaled0];"
                    f"[bgblur0][fgscaled0]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30[vout];"
                )
            else:
                filter_parts.append(
                    f"[0:v:0]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30[vout];"
                )
        else:
            for idx in range(num_vids):
                if fit_mode == "blur_bg":
                    filter_parts.append(
                        f"[{idx}:v:0]split[bg{idx}][fg{idx}];"
                        f"[bg{idx}]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=20:5[bgblur{idx}];"
                        f"[fg{idx}]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fgscaled{idx}];"
                        f"[bgblur{idx}][fgscaled{idx}]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30[v{idx}];"
                    )
                else:
                    filter_parts.append(
                        f"[{idx}:v:0]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30[v{idx}];"
                    )
            concat_v = "".join([f"[v{i}]" for i in range(num_vids)])
            filter_parts.append(f"{concat_v}concat=n={num_vids}:v=1:a=0[vout];")

        # Voice audio stream filter
        if has_voice:
            if len(voice_indices) == 1:
                idx = voice_indices[0]
                if duration_mode == "loop_voice":
                    filter_parts.append(f"[{idx}:a:0]volume=1.0,aloop=loop=-1:size=2147483647,apad[a_voice];")
                else:
                    filter_parts.append(f"[{idx}:a:0]volume=1.0,apad[a_voice];")
            else:
                concat_voice_inputs = "".join([f"[{i}:a:0]" for i in voice_indices])
                filter_parts.append(f"{concat_voice_inputs}concat=n={len(voice_indices)}:v=0:a=1[a_voice_raw];")
                if duration_mode == "loop_voice":
                    filter_parts.append(f"[a_voice_raw]volume=1.0,aloop=loop=-1:size=2147483647,apad[a_voice];")
                else:
                    filter_parts.append(f"[a_voice_raw]volume=1.0,apad[a_voice];")
            audio_mix_streams.append("[a_voice]")

        # BGM audio stream filter
        if has_bgm:
            filter_parts.append(f"[{bgm_idx}:a:0]volume={bgm_volume:.2f},aloop=loop=-1:size=2147483647,apad[a_bgm];")
            audio_mix_streams.append("[a_bgm]")

        # Original video audio stream filter
        if not remove_original_audio:
            if num_vids == 1:
                filter_parts.append("[0:a:0]volume=1.0[a_orig];")
            else:
                concat_a = "".join([f"[{i}:a:0]" for i in range(num_vids)])
                filter_parts.append(f"{concat_a}concat=n={num_vids}:v=0:a=1[a_orig];")
            audio_mix_streams.append("[a_orig]")

        has_final_audio = len(audio_mix_streams) > 0
        if len(audio_mix_streams) >= 2:
            streams_str = "".join(audio_mix_streams)
            filter_parts.append(f"{streams_str}amix=inputs={len(audio_mix_streams)}:duration=first:normalize=0[aout]")
        elif len(audio_mix_streams) == 1:
            filter_parts.append(f"{audio_mix_streams[0]}anull[aout]")

        full_filter = "".join(filter_parts)
        time_args = ["-t", str(target_dur)] if target_dur > 0 else []

        cmd = [
            ffmpeg_bin, "-y",
            "-threads", "0",
            *inputs,
            "-filter_complex", full_filter,
            "-map", "[vout]",
            *(["-map", "[aout]"] if has_final_audio else ["-an"]),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            *(["-c:a", "aac", "-b:a", "192k"] if has_final_audio else []),
            *time_args,
            "-shortest",
            str(output_filepath)
        ]

        print(f"[*] Running FFmpeg 9:16 vertical encoding command ({target_w}x{target_h})...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if res.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
            print(f"[!] FFmpeg error output:\n{res.stderr}")
            raise RuntimeError(f"FFmpeg process failed: {res.stderr}")

        file_size = output_filepath.stat().st_size
        final_duration = cls.get_video_duration(output_filepath)
        print(f"[OK] 9:16 Vertical Video complete! Output: {output_filename} ({round(file_size / (1024*1024), 2)} MB, {final_duration:.2f}s, {target_w}x{target_h})")

        return {
            "id": video_id,
            "has_voice": has_voice,
            "voice_count": len(valid_audio_paths),
            "has_bgm": has_bgm,
            "bgm_volume": bgm_volume,
            "voice_duration": voice_dur,
            "filename": output_filename,
            "file_size": file_size,
            "video_duration": final_duration,
            "video_count": num_vids,
            "duration_mode": duration_mode,
            "remove_original_audio": remove_original_audio,
            "aspect_ratio": aspect_ratio,
            "resolution": f"{target_w}x{target_h}"
        }
