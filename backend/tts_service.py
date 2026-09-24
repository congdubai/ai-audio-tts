import sys
import os
import uuid
import time
import io
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

# Add kokoro-vi-ngoc-huyen repository to sys.path
MODEL_REPO_DIR = Path(__file__).resolve().parent.parent / "kokoro-vi-ngoc-huyen"
if str(MODEL_REPO_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_REPO_DIR))

try:
    from infer import KokoroVietnameseTTS
except ImportError:
    KokoroVietnameseTTS = None

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
        print(f"[*] Initializing Kokoro Vietnamese TTS Engine on device: {self.device.upper()}...")
        
        model_path = MODEL_REPO_DIR / "model" / "kokoro_vi_ngoc_huyen.pth"
        voicepack_path = MODEL_REPO_DIR / "voices" / "ngoc_huyen.pt"
        config_path = MODEL_REPO_DIR / "config.json"

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at: {model_path}")
        if not voicepack_path.exists():
            raise FileNotFoundError(f"Voicepack file not found at: {voicepack_path}")
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at: {config_path}")

        self.tts_model = KokoroVietnameseTTS(
            model_path=str(model_path),
            voicepack_path=str(voicepack_path),
            config_path=str(config_path),
            device=self.device
        )
        self.is_ready = True
        print(f"[OK] Kokoro Vietnamese TTS Model loaded successfully! (Voice: Ngoc Huyen)")

    def synthesize(self, text: str, speed: float = 1.0) -> Dict[str, Any]:
        if not self.is_ready or self.tts_model is None:
            self.initialize()

        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Văn bản không được để trống.")

        start_time = time.time()
        sample_rate, audio_np, phonemes = self.tts_model.synthesize(clean_text, speed=speed)
        elapsed_time = round(time.time() - start_time, 3)

        duration = round(len(audio_np) / sample_rate, 2)
        audio_id = str(uuid.uuid4())
        filename = f"{audio_id}.wav"
        file_path = OUTPUTS_DIR / filename

        # Write to WAV file
        sf.write(str(file_path), audio_np, sample_rate)
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
            "device": self.device
        }

    def get_audio_path(self, filename: str) -> Optional[Path]:
        file_path = OUTPUTS_DIR / filename
        if file_path.exists() and file_path.is_file():
            return file_path
        return None
