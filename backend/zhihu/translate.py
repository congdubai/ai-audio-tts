"""Dịch Việt <-> Trung bằng Ollama chạy local (không dùng API trả phí)."""
from __future__ import annotations

import unicodedata

import requests

from . import config


class OllamaError(RuntimeError):
    """Lỗi liên quan Ollama, message đã viết sẵn bằng tiếng Việt."""


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower().strip()


def list_models() -> list[str]:
    """Danh sách model Ollama đã pull. Ném OllamaError nếu Ollama chưa chạy."""
    try:
        r = requests.get(config.OLLAMA_TAGS_URL, timeout=5)
        r.raise_for_status()
    except requests.ConnectionError:
        raise OllamaError(
            "Không kết nối được Ollama tại localhost:11434. "
            "Hãy cài Ollama (https://ollama.com) và mở ứng dụng Ollama, hoặc chạy 'ollama serve'."
        )
    except requests.RequestException as e:
        raise OllamaError(f"Ollama trả về lỗi: {e}")
    return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]


def check_ollama(model: str) -> None:
    """Đảm bảo Ollama đang chạy và đã có model cần dùng."""
    models = list_models()
    if model not in models and f"{model}:latest" not in models:
        have = ", ".join(models) if models else "(chưa có model nào)"
        raise OllamaError(
            f"Ollama chưa có model '{model}'. Chạy lệnh: ollama pull {model}. Model hiện có: {have}"
        )


def ollama(prompt: str, model: str = config.OLLAMA_DEFAULT_MODEL) -> str:
    try:
        r = requests.post(
            config.OLLAMA_GENERATE_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": config.OLLAMA_TEMPERATURE},
            },
            timeout=config.OLLAMA_TIMEOUT,
        )
    except requests.ConnectionError:
        raise OllamaError("Mất kết nối tới Ollama trong lúc dịch. Kiểm tra Ollama còn đang chạy không.")
    except requests.Timeout:
        raise OllamaError(f"Ollama dịch quá {config.OLLAMA_TIMEOUT}s không phản hồi (máy có thể đang quá tải).")
    if r.status_code == 404:
        raise OllamaError(f"Ollama không tìm thấy model '{model}'. Chạy: ollama pull {model}")
    if not r.ok:
        raise OllamaError(f"Ollama lỗi HTTP {r.status_code}: {r.text[:200]}")
    return r.json().get("response", "").strip()


def to_chinese(keyword: str, model: str = config.OLLAMA_DEFAULT_MODEL) -> tuple[str, str]:
    """Đổi từ khoá Việt -> Trung. Ưu tiên GENRE_MAP, không có thì nhờ model dịch.

    Trả về (từ_khoá_trung, nguồn) với nguồn là "map" hoặc "ollama".
    """
    key = strip_accents(keyword)
    lookup = {strip_accents(k): v for k, v in config.GENRE_MAP.items()}
    if key in lookup:
        return lookup[key], "map"
    out = ollama(
        "Dịch từ khoá thể loại truyện sau từ tiếng Việt sang tiếng Trung "
        "(thuật ngữ web novel Trung Quốc). Chỉ trả lời bằng chữ Hán, không giải thích.\n"
        f"Từ khoá: {keyword}",
        model=model,
    )
    first = out.splitlines()[0].strip() if out else ""
    if not first:
        raise OllamaError(f"Model không trả về bản dịch cho từ khoá '{keyword}'.")
    return first, "ollama"


def to_vietnamese(text: str, model: str = config.OLLAMA_DEFAULT_MODEL) -> str:
    if not text or not text.strip():
        return ""
    return ollama(
        "Dịch đoạn tiếng Trung sau sang tiếng Việt tự nhiên, giữ văn phong "
        "giới thiệu/review truyện. Chỉ trả về bản dịch.\n\n" + text[: config.MAX_TRANSLATE_CHARS],
        model=model,
    )
