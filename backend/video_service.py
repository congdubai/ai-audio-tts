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
        duration_mode: str = "full_video"  # "full_video" | "match_voice" | "loop_voice"
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

        print(f"[*] Processing Video ({len(video_paths)} video clips, {len(valid_audio_paths)} voice audio clips). Voice total: {voice_dur:.2f}s, BGM: {'Yes (' + str(bgm_dur) + 's, vol=' + str(bgm_volume) + ')' if has_bgm else 'No'}, Mute orig: {remove_original_audio}, Mode: {duration_mode}")

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

        filter_parts = []

        # Video Filter Concat / Scale
        if num_vids == 1:
            video_dur = cls.get_video_duration(video_paths[0])
            filter_parts.append("[0:v:0]null[vout];")
        else:
            video_dur = sum(cls.get_video_duration(vp) for vp in video_paths)
            for idx in range(num_vids):
                filter_parts.append(
                    f"[{idx}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-ih)/2:(oh-ih)/2,setsar=1,fps=30[v{idx}];"
                )
            concat_v = "".join([f"[v{i}]" for i in range(num_vids)])
            filter_parts.append(f"{concat_v}concat=n={num_vids}:v=1:a=0[vout];")

        # Determine target duration
        if duration_mode == "match_voice" and has_voice and voice_dur > 0:
            target_dur = voice_dur
        else:
            target_dur = video_dur

        # Audio Stream Filters
        audio_mix_streams = []

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

        if has_bgm:
            filter_parts.append(f"[{bgm_idx}:a:0]volume={bgm_volume:.2f},aloop=loop=-1:size=2147483647,apad[a_bgm];")
            audio_mix_streams.append("[a_bgm]")

        if not remove_original_audio:
            if num_vids == 1:
                filter_parts.append("[0:a:0]volume=1.0[a_orig];")
            else:
                concat_a = "".join([f"[{i}:a:0]" for i in range(num_vids)])
                filter_parts.append(f"{concat_a}concat=n={num_vids}:v=0:a=1[a_orig];")
            audio_mix_streams.append("[a_orig]")

        # Combine audio streams
        if len(audio_mix_streams) >= 2:
            streams_str = "".join(audio_mix_streams)
            filter_parts.append(f"{streams_str}amix=inputs={len(audio_mix_streams)}:duration=first:normalize=0[aout]")
            has_final_audio = True
        elif len(audio_mix_streams) == 1:
            filter_parts.append(f"{audio_mix_streams[0]}anull[aout]")
            has_final_audio = True
        else:
            has_final_audio = False

        full_filter = "".join(filter_parts)

        # Build FFmpeg command
        cmd = [
            ffmpeg_bin, "-y",
            "-threads", "0",
            *inputs,
            "-filter_complex", full_filter,
            "-map", "[vout]",
            *(["-map", "[aout]"] if has_final_audio else ["-an"]),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            *(["-c:a", "aac", "-b:a", "192k"] if has_final_audio else []),
            *(["-t", str(target_dur)] if target_dur > 0 else []),
            str(output_filepath)
        ]

        print("[*] Running FFmpeg complex filter command...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0 or not output_filepath.exists() or output_filepath.stat().st_size == 0:
            print(f"[!] FFmpeg error output:\n{result.stderr}")
            raise RuntimeError(f"FFmpeg process failed: {result.stderr}")

        file_size = output_filepath.stat().st_size
        final_duration = cls.get_video_duration(output_filepath)
        print(f"[OK] Video processing complete! Output: {output_filename} ({round(file_size / (1024*1024), 2)} MB, {final_duration:.2f}s)")

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
            "remove_original_audio": remove_original_audio
        }
