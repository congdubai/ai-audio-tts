import sys
import os
import uuid
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add kokoro-vi-ngoc-huyen directory to sys.path
KOKORO_DIR = Path(__file__).parent.parent / "kokoro-vi-ngoc-huyen"
if KOKORO_DIR.exists() and str(KOKORO_DIR) not in sys.path:
    sys.path.insert(0, str(KOKORO_DIR))

# Fix Windows console encoding for Vietnamese characters
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

OUTPUTS_DIR = Path(__file__).parent / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


class TTSEngine:
    _instance: Optional['TTSEngine'] = None
    tts_model: Optional[Any] = None
    device: str = "cpu"
    is_ready: bool = False

    @classmethod
    def get_instance(cls) -> 'TTSEngine':
        if cls._instance is None:
            cls._instance = TTSEngine()
        return cls._instance

    def initialize(self):
        if self.is_ready:
            return

        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[*] Initializing Kokoro Vietnamese TTS on device: {self.device.upper()}...")

        try:
            from infer import KokoroVietnameseTTS
        except ImportError:
            raise ImportError(
                "Could not import KokoroVietnameseTTS from kokoro-vi-ngoc-huyen directory."
            )

        self.tts_model = KokoroVietnameseTTS(device=self.device)
        self.is_ready = True
        print(f"[OK] Kokoro Vietnamese TTS loaded successfully! (device: {self.device.upper()})")

    def synthesize(self, text: str, speed: float = 1.0, progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        if not self.is_ready or self.tts_model is None:
            self.initialize()

        import soundfile as sf

        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Văn bản không được để trống.")

        start_time = time.time()

        sample_rate, audio, phonemes = self.tts_model.synthesize(
            clean_text,
            speed=speed,
            progress_callback=progress_callback
        )

        elapsed_time = round(time.time() - start_time, 3)
        duration = round(len(audio) / sample_rate, 2)
        audio_id = str(uuid.uuid4())
        filename = f"{audio_id}.wav"
        file_path = OUTPUTS_DIR / filename

        sf.write(str(file_path), audio, sample_rate, subtype='PCM_16')
        file_size = file_path.stat().st_size

        return {
            "id": audio_id,
            "text": clean_text,
            "speed": speed,
            "duration": duration,
            "sample_rate": sample_rate,
            "phonemes": phonemes,
            "filename": filename,
            "file_size": file_size,
            "elapsed_time": elapsed_time,
            "device": self.device,
        }

    def get_audio_path(self, filename: str) -> Optional[Path]:
        file_path = OUTPUTS_DIR / filename
        if file_path.exists() and file_path.is_file():
            return file_path
        return None
