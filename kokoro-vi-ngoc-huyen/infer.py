#!/usr/bin/env python3
"""Inference-only Vietnamese Kokoro TTS for the Ngoc Huyen voice."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np


DEFAULT_REPO_ID = "dinhthuan/kokoro-vi-ngoc-huyen"
DEFAULT_MODEL_FILE = "model/kokoro_vi_ngoc_huyen.pth"
DEFAULT_VOICEPACK_FILE = "voices/ngoc_huyen.pt"
DEFAULT_CONFIG_FILE = "config.json"
SAMPLE_RATE = 24000
DEFAULT_CROSSFADE_MS = 50


def split_text(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    for match in re.finditer(r'[.!?…]+(?:["”’)]*)', normalized):
        end = match.end()
        if end < len(normalized) and not normalized[end].isspace():
            continue
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end

    remainder = normalized[start:].strip()
    if remainder:
        chunks.append(remainder)
    return chunks


def merge_audio_chunks(chunks: list[np.ndarray], crossfade_ms: int = DEFAULT_CROSSFADE_MS) -> np.ndarray:
    valid_chunks = [np.asarray(chunk, dtype=np.float32) for chunk in chunks if len(chunk) > 0]
    if not valid_chunks:
        return np.array([], dtype=np.float32)

    crossfade_samples = round(SAMPLE_RATE * int(crossfade_ms) / 1000)
    merged = valid_chunks[0]
    for chunk in valid_chunks[1:]:
        overlap = min(crossfade_samples, len(merged), len(chunk))
        if overlap <= 0:
            merged = np.concatenate([merged, chunk])
            continue
        fade_out = np.linspace(1.0, 0.0, overlap + 2, dtype=np.float32)[1:-1]
        fade_in = 1.0 - fade_out
        crossfaded = merged[-overlap:] * fade_out + chunk[:overlap] * fade_in
        merged = np.concatenate([merged[:-overlap], crossfaded, chunk[overlap:]])
    return merged.astype(np.float32, copy=False)


def _repo_file(repo_id: str, filename: str, local_path: str | Path | None = None) -> Path:
    if local_path:
        path = Path(local_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    bundled_path = Path(__file__).resolve().parent / filename
    if bundled_path.exists():
        return bundled_path

    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=repo_id, filename=filename))


class KokoroVietnameseTTS:
    """Small reusable API that loads the model once and synthesizes many texts."""

    def __init__(
        self,
        repo_id: str = DEFAULT_REPO_ID,
        model_path: str | Path | None = None,
        voicepack_path: str | Path | None = None,
        config_path: str | Path | None = None,
        device: str = "cuda",
    ):
        import torch
        from kokoro import KModel, KPipeline

        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"

        self.device = device
        self.model_path = _repo_file(repo_id, DEFAULT_MODEL_FILE, model_path)
        self.voicepack_path = _repo_file(repo_id, DEFAULT_VOICEPACK_FILE, voicepack_path)
        self.config_path = _repo_file(repo_id, DEFAULT_CONFIG_FILE, config_path)

        self.model = KModel(
            repo_id="hexgrad/Kokoro-82M",
            config=str(self.config_path),
            model=str(self.model_path),
        ).to(device).eval()
        self.pipeline = KPipeline(
            lang_code="v",
            repo_id="hexgrad/Kokoro-82M",
            model=self.model,
        )
        self.voice = torch.load(self.voicepack_path, map_location="cpu", weights_only=True)

    def synthesize(
        self,
        text: str,
        speed: float = 1.0,
        crossfade_ms: int = DEFAULT_CROSSFADE_MS,
    ) -> tuple[int, np.ndarray, str]:
        chunks: list[np.ndarray] = []
        phoneme_chunks: list[str] = []

        for index, text_chunk in enumerate(split_text(text), start=1):
            for _, phonemes, audio in self.pipeline(
                text_chunk,
                voice=self.voice,
                speed=float(speed),
                split_pattern=None,
            ):
                if phonemes:
                    phoneme_chunks.append(f"[{index}] {phonemes}")
                if audio is not None:
                    chunks.append(audio.detach().cpu().numpy())

        audio = merge_audio_chunks(chunks, crossfade_ms=crossfade_ms)
        if len(audio) == 0:
            raise RuntimeError("No audio generated.")
        return SAMPLE_RATE, audio, "\n".join(phoneme_chunks)

    def save_wav(
        self,
        text: str,
        output: str | Path,
        speed: float = 1.0,
        crossfade_ms: int = DEFAULT_CROSSFADE_MS,
    ) -> tuple[Path, str]:
        import soundfile as sf

        sample_rate, audio, phonemes = self.synthesize(
            text,
            speed=speed,
            crossfade_ms=crossfade_ms,
        )
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, audio, sample_rate)
        return output_path, phonemes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vietnamese Kokoro Ngoc Huyen inference")
    parser.add_argument("--text", required=True, help="Vietnamese text to synthesize")
    parser.add_argument("--output", default="outputs/ngoc_huyen.wav", help="Output WAV path")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="Hugging Face model repo")
    parser.add_argument("--model", help=f"Local model path. Defaults to {DEFAULT_MODEL_FILE}.")
    parser.add_argument("--voicepack", help=f"Local voicepack path. Defaults to {DEFAULT_VOICEPACK_FILE}.")
    parser.add_argument("--config", help=f"Local config path. Defaults to {DEFAULT_CONFIG_FILE}.")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="Inference device")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    parser.add_argument("--crossfade-ms", type=int, default=DEFAULT_CROSSFADE_MS, help="Sentence merge crossfade")
    parser.add_argument("--print-phonemes", action="store_true", help="Print generated phonemes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tts = KokoroVietnameseTTS(
        repo_id=args.repo_id,
        model_path=args.model,
        voicepack_path=args.voicepack,
        config_path=args.config,
        device=args.device,
    )
    output, phonemes = tts.save_wav(
        args.text,
        args.output,
        speed=args.speed,
        crossfade_ms=args.crossfade_ms,
    )
    if args.print_phonemes and phonemes:
        print(phonemes)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
