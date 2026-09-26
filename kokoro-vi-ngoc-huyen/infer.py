#!/usr/bin/env python3
"""Inference-only Vietnamese Kokoro TTS for the Ngoc Huyen voice."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import numpy as np


DEFAULT_REPO_ID = "dinhthuan/kokoro-vi-ngoc-huyen"
DEFAULT_MODEL_FILE = "model/kokoro_vi_ngoc_huyen.pth"
DEFAULT_VOICEPACK_FILE = "voices/ngoc_huyen.pt"
DEFAULT_CONFIG_FILE = "config.json"
SAMPLE_RATE = 24000
DEFAULT_CROSSFADE_MS = 50
MAX_CHUNK_CHARS = 200


def _split_by_words(text: str, max_chars: int) -> list[str]:
    """Split a long text block into pieces of at most max_chars by word boundaries."""
    words = text.split()
    if not words:
        return []
    result: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        if len(word) > max_chars:
            if current:
                result.append(" ".join(current))
                current = []
                current_len = 0
            for i in range(0, len(word), max_chars):
                result.append(word[i : i + max_chars])
            continue

        added_len = len(word) if current_len == 0 else len(word) + 1
        if current_len + added_len <= max_chars:
            current.append(word)
            current_len += added_len
        else:
            result.append(" ".join(current))
            current = [word]
            current_len = len(word)

    if current:
        result.append(" ".join(current))
    return result


def _split_long_sentence(sentence: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split a sentence longer than max_chars by sub-punctuation (, ; : – —), or word boundaries."""
    sentence = sentence.strip()
    if not sentence:
        return []

    if len(sentence) <= max_chars:
        return [sentence]

    # Split by sub-punctuation: , ; : – —
    parts = re.split(r"([,;:–—]+(?:\s+|$))", sentence)

    clauses: list[str] = []
    i = 0
    while i < len(parts):
        text_part = parts[i]
        punc_part = parts[i + 1] if i + 1 < len(parts) else ""
        clause = (text_part + punc_part).strip()
        if clause:
            clauses.append(clause)
        i += 2

    if not clauses:
        clauses = [sentence]

    # Combine clauses up to max_chars
    result: list[str] = []
    current_clause = ""

    for clause in clauses:
        if len(clause) > max_chars:
            if current_clause:
                result.append(current_clause.strip())
                current_clause = ""
            sub_pieces = _split_by_words(clause, max_chars)
            for piece in sub_pieces:
                if len(piece) <= max_chars:
                    if not current_clause:
                        current_clause = piece
                    elif len(current_clause) + 1 + len(piece) <= max_chars:
                        current_clause = current_clause + " " + piece
                    else:
                        result.append(current_clause.strip())
                        current_clause = piece
                else:
                    if current_clause:
                        result.append(current_clause.strip())
                        current_clause = ""
                    result.append(piece)
        else:
            if not current_clause:
                current_clause = clause
            elif len(current_clause) + 1 + len(clause) <= max_chars:
                current_clause = current_clause + " " + clause
            else:
                result.append(current_clause.strip())
                current_clause = clause

    if current_clause:
        result.append(current_clause.strip())

    return result


def normalize_for_tts(text: str) -> str:
    """Clean markdown markers (#, **, *, >) from text prior to TTS synthesis."""
    if not text:
        return ""

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Remove leading markdown heading markers (#, ##, ###, ...)
        line = re.sub(r"^#{1,6}\s*", "", line)
        # Remove leading blockquote markers (>)
        line = re.sub(r"^>\s*", "", line)
        # Remove bold/italic markdown symbols (*, **, ***), keeping inner text
        line = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", line)
        # Remove remaining stray asterisks if any
        line = line.replace("*", "")

        line = line.strip()
        if line:
            cleaned_lines.append(line)

    joined = " ".join(cleaned_lines)
    return re.sub(r"\s+", " ", joined).strip()


def split_text(text: str) -> list[str]:
    clean_text = normalize_for_tts(text)
    if not clean_text:
        return []

    raw_chunks: list[str] = []
    start = 0
    for match in re.finditer(r'[.!?…]+(?:["”’)]*)', clean_text):
        end = match.end()
        if end < len(clean_text) and not clean_text[end].isspace():
            continue
        chunk = clean_text[start:end].strip()
        if chunk:
            raw_chunks.append(chunk)
        start = end

    remainder = clean_text[start:].strip()
    if remainder:
        raw_chunks.append(remainder)

    final_chunks: list[str] = []
    for chunk in raw_chunks:
        if len(chunk) > MAX_CHUNK_CHARS:
            final_chunks.extend(_split_long_sentence(chunk, MAX_CHUNK_CHARS))
        else:
            final_chunks.append(chunk)

    return final_chunks


def _apply_edge_fade(chunk: np.ndarray, fade_ms: float = 8.0) -> np.ndarray:
    """Apply micro fade-in and fade-out to chunk boundaries to prevent DC offset clicks/pops."""
    if len(chunk) == 0:
        return chunk
    n = round(SAMPLE_RATE * fade_ms / 1000)
    n = min(n, len(chunk) // 2)
    if n <= 0:
        return chunk

    faded = np.asarray(chunk, dtype=np.float32).copy()
    fade_in = np.linspace(0.0, 1.0, n, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, n, dtype=np.float32)

    faded[:n] *= fade_in
    faded[-n:] *= fade_out
    return faded


def merge_audio_chunks(
    chunks: list[np.ndarray],
    crossfade_ms: int = DEFAULT_CROSSFADE_MS,
    fade_ms: float = 8.0,
) -> np.ndarray:
    valid_chunks = [np.asarray(chunk, dtype=np.float32) for chunk in chunks if len(chunk) > 0]
    if not valid_chunks:
        return np.array([], dtype=np.float32)

    # Apply edge micro-fades to eliminate boundary click/pop sounds
    faded_chunks = [_apply_edge_fade(chunk, fade_ms=fade_ms) for chunk in valid_chunks]

    # 180ms natural silence pause between chunks
    pause_samples = round(SAMPLE_RATE * 0.180)
    pause = np.zeros(pause_samples, dtype=np.float32)

    parts: list[np.ndarray] = []
    for idx, chunk in enumerate(faded_chunks):
        parts.append(chunk)
        if idx < len(faded_chunks) - 1:
            parts.append(pause)

    merged = np.concatenate(parts)

    # Peak normalization to target 0.90 for uniform volume and clipping prevention
    max_val = float(np.max(np.abs(merged))) if len(merged) > 0 else 0.0
    if max_val > 0.0:
        merged = merged * (0.90 / max_val)

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
        print(f"[*] Engine initialized: Kokoro Vietnamese TTS (Device: {self.device.upper()} | Features: Clean Markdown, Max 200-Char Chunking, Edge Fade 8ms, Checkpoint Support)")

    def synthesize(
        self,
        text: str,
        speed: float = 1.0,
        crossfade_ms: int = DEFAULT_CROSSFADE_MS,
        checkpoint_dir: str | Path | None = None,
    ) -> tuple[int, np.ndarray, str]:
        import soundfile as sf

        start_time = time.time()
        text_chunks = split_text(text)
        total_chunks = len(text_chunks)

        if total_chunks == 0:
            return SAMPLE_RATE, np.array([], dtype=np.float32), ""

        chk_path: Path | None = None
        if checkpoint_dir is not None:
            chk_path = Path(checkpoint_dir).expanduser().resolve()
            chk_path.mkdir(parents=True, exist_ok=True)

        chunks: list[np.ndarray] = []
        phoneme_chunks: list[str] = []

        try:
            for index, text_chunk in enumerate(text_chunks, start=1):
                preview = text_chunk[:40] + "..." if len(text_chunk) > 40 else text_chunk
                print(f"[TTS] Đang xử lý chunk {index}/{total_chunks}: {preview}...")

                chunk_audio: np.ndarray | None = None

                # Check if checkpoint exists
                if chk_path is not None:
                    chk_file = chk_path / f"chunk_{index:04d}.wav"
                    if chk_file.exists():
                        try:
                            data, _ = sf.read(str(chk_file), dtype="float32")
                            chunk_audio = data
                            print(f"[TTS] [Resume] Chunk {index}/{total_chunks} đã có sẵn tại checkpoint. Đang nạp lại...")
                        except Exception as e:
                            print(f"[TTS] [Warning] Lỗi khi đọc checkpoint {chk_file.name}, tiến hành tạo mới: {e}")
                            chunk_audio = None

                # Generate chunk if not loaded from checkpoint
                if chunk_audio is None:
                    chunk_parts: list[np.ndarray] = []
                    for _, phonemes, audio in self.pipeline(
                        text_chunk,
                        voice=self.voice,
                        speed=float(speed),
                        split_pattern=None,
                    ):
                        if phonemes:
                            phoneme_chunks.append(f"[{index}] {phonemes}")
                        if audio is not None:
                            chunk_parts.append(audio.detach().cpu().numpy())

                    if chunk_parts:
                        chunk_audio = np.concatenate(chunk_parts)
                    else:
                        chunk_audio = np.array([], dtype=np.float32)

                    # Save checkpoint immediately if checkpoint_dir is specified
                    if chk_path is not None and len(chunk_audio) > 0:
                        chk_file = chk_path / f"chunk_{index:04d}.wav"
                        try:
                            sf.write(str(chk_file), chunk_audio, SAMPLE_RATE)
                        except Exception as e:
                            print(f"[TTS] [Warning] Không thể lưu checkpoint {chk_file.name}: {e}")

                if chunk_audio is not None and len(chunk_audio) > 0:
                    chunks.append(chunk_audio)

        except KeyboardInterrupt:
            stop_msg = f"\n[TTS] Đã dừng tại chunk {index}/{total_chunks}."
            if chk_path is not None:
                stop_msg += f" Các chunk đã xử lý được lưu tại {chk_path}, chạy lại lệnh với cùng --checkpoint-dir để tiếp tục."
            print(stop_msg)
            sys.exit(1)

        audio = merge_audio_chunks(chunks, crossfade_ms=crossfade_ms)
        if len(audio) == 0:
            raise RuntimeError("No audio generated.")

        elapsed = time.time() - start_time
        print(f"[TTS] Hoàn thành tổng hợp giọng nói trong {elapsed:.2f} giây.")

        return SAMPLE_RATE, audio, "\n".join(phoneme_chunks)

    def save_wav(
        self,
        text: str,
        output: str | Path,
        speed: float = 1.0,
        crossfade_ms: int = DEFAULT_CROSSFADE_MS,
        checkpoint_dir: str | Path | None = None,
    ) -> tuple[Path, str]:
        import soundfile as sf

        sample_rate, audio, phonemes = self.synthesize(
            text,
            speed=speed,
            crossfade_ms=crossfade_ms,
            checkpoint_dir=checkpoint_dir,
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
    parser.add_argument("--checkpoint-dir", help="Thư mục lưu tạm audio từng câu để tiếp tục nếu bị ngắt giữa chừng")
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
        checkpoint_dir=args.checkpoint_dir,
    )
    if args.print_phonemes and phonemes:
        print(phonemes)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

