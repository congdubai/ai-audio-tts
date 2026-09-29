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
DEFAULT_PAUSE_MS = 120


def sanitize_text(text: str) -> str:
    import re
    # 1. Loại markdown blockquote/heading/list markers ở đầu dòng: >, #, -, *, +
    text = re.sub(r'(?m)^[ \t]*[>#\-\*\+]+[ \t]*', '', text)
    # 2. Loại toàn bộ ký tự ngoặc kép/nháy các loại
    text = re.sub(r'["”’“‘\'\`«»]', '', text)
    # 3. Thay MỌI biến thể ba chấm (..., . . ., …, kể cả dính liền chữ) bằng dấu phẩy
    text = re.sub(r'\.{2,}|…', ',', text)
    # 4. Loại markdown in đậm/nghiêng còn sót: **, __, _, *
    text = re.sub(r'[*_]{1,2}', '', text)
    # 5. Dọn dẹp khoảng trắng & dấu phẩy dính với hai chấm hoặc đứng đầu/cuối câu
    text = re.sub(r'\s*:\s*,', ':', text)
    text = re.sub(r'\s*,\s*,+', ',', text)
    text = re.sub(r'^\s*,\s*', '', text)
    text = re.sub(r'(?<=[.!?]),', '', text)
    text = re.sub(r',(?=[.!?])', '', text)
    text = re.sub(r'\.(?=[.!?])', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def split_text(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []

    raw_chunks: list[str] = []
    start = 0
    for match in re.finditer(r'[.!?…]+(?:["”’)]*)', normalized):
        end = match.end()
        if end < len(normalized) and not normalized[end].isspace():
            continue
        chunk = normalized[start:end].strip()
        if chunk:
            raw_chunks.append(chunk)
        start = end

    remainder = normalized[start:].strip()
    if remainder:
        raw_chunks.append(remainder)

    if not raw_chunks:
        return []

    # 1. Lọc và gộp các chunk không chứa ký tự chữ cái (\w) vào chunk liền trước
    #    để tránh tạo chunk phoneme-rỗng gây crack khi ghép
    merged_chunks: list[str] = []
    for chunk in raw_chunks:
        if not re.search(r"\w", chunk):
            # Chunk rỗng về mặt ngữ âm → gộp vào chunk liền trước
            if merged_chunks:
                merged_chunks[-1] = f"{merged_chunks[-1]} {chunk}".strip()
            # Nếu chưa có chunk nào thì bỏ qua hẳn (không thêm vào)
        else:
            merged_chunks.append(chunk)

    # 2. Hybrid: câu hoàn chỉnh (kết thúc .!?…) và đủ dài → chunk riêng (nhịp tự nhiên)
    #            câu siêu ngắn < MIN_STANDALONE → gộp vào câu kề (tránh crack do model)
    # Giải thích: model Kokoro cần đủ context âm học để sinh audio mượt.
    # Câu 1-2 từ ("À.", "Chào.") không đủ context → model sinh transient cứng → crack.
    # Gộp vào câu kề giúp model đọc trong context đầy đủ hơn.
    _SENTENCE_END = re.compile(r"[.!?…]+\s*$")
    MIN_STANDALONE = 10  # ký tự tối thiểu để câu đứng riêng thành 1 chunk

    grouped: list[str] = []
    pending = ""  # fragment chưa hoàn chỉnh hoặc quá ngắn

    for chunk in merged_chunks:
        if pending:
            chunk = f"{pending} {chunk}".strip()
            pending = ""

        is_complete = bool(_SENTENCE_END.search(chunk))
        is_long_enough = len(chunk) >= MIN_STANDALONE

        if is_complete and is_long_enough:
            # Câu hoàn chỉnh, đủ dài → chunk riêng, hưởng pause_ms giữa các câu
            grouped.append(chunk)
        else:
            # Câu quá ngắn hoặc chưa kết thúc → gộp vào câu tiếp để model có context
            pending = chunk

    # Chunk cuối còn pending → gộp vào câu cuối hoặc thêm mới
    if pending:
        if grouped:
            grouped[-1] = f"{grouped[-1]} {pending}".strip()
        else:
            grouped.append(pending)

    return grouped


def merge_audio_chunks(
    chunks: list[np.ndarray],
    crossfade_ms: int = DEFAULT_CROSSFADE_MS,
    pause_ms: int = DEFAULT_PAUSE_MS,
    micro_fade_ms: int = 8,
    min_chunk_ms: int = 120,
    edge_pad_ms: int = 25,
) -> np.ndarray:
    valid_chunks = [np.asarray(chunk, dtype=np.float32) for chunk in chunks if len(chunk) > 0]
    if not valid_chunks:
        return np.array([], dtype=np.float32)

    fade_samples = int(SAMPLE_RATE * micro_fade_ms / 1000)
    pause_samples = int(SAMPLE_RATE * pause_ms / 1000)
    silence = np.zeros(pause_samples, dtype=np.float32)

    min_chunk_samples = int(SAMPLE_RATE * min_chunk_ms / 1000)
    edge_pad_samples = int(SAMPLE_RATE * edge_pad_ms / 1000)
    silence_pad = np.zeros(edge_pad_samples, dtype=np.float32)

    processed_chunks: list[np.ndarray] = []
    for chunk in valid_chunks:
        c = chunk.copy()

        if len(c) < min_chunk_samples:
            # Chunk quá ngắn: fade phải áp dụng vào CHÍNH audio TTS trước,
            # rồi mới ghép silence padding ra ngoài.
            # Nếu làm ngược (pad trước rồi fade sau) → fade chỉ tác động vào
            # silence (đã =0) → audio TTS vẫn bắt đầu/kết thúc đột ngột → crack!
            inner_fade = min(fade_samples, len(c) // 3)
            if inner_fade > 0:
                c[:inner_fade] *= np.linspace(0.0, 1.0, inner_fade, dtype=np.float32)
                c[-inner_fade:] *= np.linspace(1.0, 0.0, inner_fade, dtype=np.float32)
            # Ghép silence padding ra ngoài audio đã được fade
            c = np.concatenate([silence_pad, c, silence_pad])
        else:
            # Chunk bình thường: fade trực tiếp vào audio
            n = len(c)
            actual_fade = min(fade_samples, n // 4)
            if actual_fade > 0:
                c[:actual_fade] *= np.linspace(0.0, 1.0, actual_fade, dtype=np.float32)
                c[-actual_fade:] *= np.linspace(1.0, 0.0, actual_fade, dtype=np.float32)

        processed_chunks.append(c)

    result: list[np.ndarray] = []
    for i, c in enumerate(processed_chunks):
        if i > 0 and pause_samples > 0:
            result.append(silence)
        result.append(c)

    merged = np.concatenate(result)

    # Normalize peak amplitude to 0.95 to avoid clipping / distortion in 16-bit WAV
    max_val = np.max(np.abs(merged))
    if max_val > 0.95:
        merged = (merged / max_val) * 0.95

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
        pause_ms: int = DEFAULT_PAUSE_MS,
        progress_callback: any = None,
    ) -> tuple[int, np.ndarray, str]:
        import torch

        clean_text = sanitize_text(text)
        if not clean_text:
            raise ValueError("Văn bản sau khi làm sạch không chứa nội dung đọc hợp lệ.")

        valid_chunks = split_text(clean_text)
        total_chunks = len(valid_chunks)

        chunks: list[np.ndarray] = []
        phoneme_chunks: list[str] = []

        with torch.inference_mode():
            for index, text_chunk in enumerate(valid_chunks, start=1):
                if progress_callback is not None:
                    try:
                        progress_callback(index, total_chunks, text_chunk)
                    except Exception:
                        pass

                # Thu thập TẤT CẢ audio segments mà pipeline yield cho 1 text chunk
                # Pipeline có thể yield nhiều segment cho 1 input → nếu append riêng lẻ
                # thì merge_audio_chunks sẽ chèn pause SAI VỊ TRÍ (giữa các segment
                # của cùng 1 câu) → crack/nhịp sai
                segment_audios: list[np.ndarray] = []
                for _, phonemes, audio in self.pipeline(
                    text_chunk,
                    voice=self.voice,
                    speed=float(speed),
                    split_pattern=None,
                ):
                    if phonemes:
                        phoneme_chunks.append(f"[{index}] {phonemes}")
                    if audio is not None:
                        segment_audios.append(audio.detach().cpu().numpy())

                # Nối các segments của cùng 1 chunk lại KHÔNG CÓ pause
                # → pause chỉ được chèn GIỮA các text chunk khác nhau
                if segment_audios:
                    chunks.append(np.concatenate(segment_audios))

        audio = merge_audio_chunks(chunks, crossfade_ms=crossfade_ms, pause_ms=pause_ms)
        if len(audio) == 0:
            raise RuntimeError("No audio generated.")
        return SAMPLE_RATE, audio, "\n".join(phoneme_chunks)

    def save_wav(
        self,
        text: str,
        output: str | Path,
        speed: float = 1.0,
        crossfade_ms: int = DEFAULT_CROSSFADE_MS,
        pause_ms: int = DEFAULT_PAUSE_MS,
    ) -> tuple[Path, str]:
        import soundfile as sf

        sample_rate, audio, phonemes = self.synthesize(
            text,
            speed=speed,
            crossfade_ms=crossfade_ms,
            pause_ms=pause_ms,
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
