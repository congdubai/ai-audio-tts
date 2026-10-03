"""Điều phối job: dịch từ khoá -> cào Zhihu -> dịch kết quả -> sắp xếp -> xuất file.

Các hàm run_* là hàm BLOCKING, được gọi trong thread worker (run_in_executor).
Tiến trình được báo qua callback `emit(dict)`.
"""
from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field

from . import config, export, translate
from .scraper import (
    JobCancelled, NoResultsError, ScraperError, ZhihuSession, login_known,
)
from .translate import OllamaError

_JOBS: dict[str, "Job"] = {}
_JOBS_LOCK = threading.Lock()


@dataclass
class Job:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    created: float = field(default_factory=time.time)


def create_job() -> Job:
    job = Job()
    with _JOBS_LOCK:
        # dọn job cũ hơn 1 giờ
        now = time.time()
        for jid in [j for j, v in _JOBS.items() if now - v.created > 3600]:
            _JOBS.pop(jid, None)
        _JOBS[job.id] = job
    return job


def cancel_job(job_id: str) -> bool:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if job:
        job.cancel_event.set()
        return True
    return False


def finish_job(job_id: str) -> None:
    with _JOBS_LOCK:
        _JOBS.pop(job_id, None)


def get_status() -> dict:
    ollama_ok, models, ollama_error = True, [], None
    try:
        models = translate.list_models()
    except OllamaError as e:
        ollama_ok, ollama_error = False, str(e)
    return {
        "ollama_running": ollama_ok,
        "ollama_models": models,
        "ollama_error": ollama_error,
        "default_model": config.OLLAMA_DEFAULT_MODEL,
        "zhihu_logged_in": login_known(),
        "genre_suggestions": list(config.GENRE_MAP.keys()),
        "max_scrolls": config.MAX_SCROLLS,
    }


def _make_emitter(emit):
    def progress(percent: float, message: str, **extra):
        emit({"type": "progress", "percent": int(max(0, min(100, percent))), "message": message, **extra})

    def log(message: str, level: str = "info"):
        emit({"type": "log", "level": level, "message": message})

    return progress, log


def run_login(job: Job, emit) -> dict:
    progress, log = _make_emitter(emit)
    progress(5, "Đang mở trình duyệt...")
    with ZhihuSession(headless=False, log=log, cancel_event=job.cancel_event) as s:
        progress(20, "Đang chờ bạn đăng nhập Zhihu...")
        s.wait_for_login()
    progress(100, "Đã đăng nhập Zhihu.")
    return {"logged_in": True}


def run_search(job: Job, emit, genres: list[str], scrolls: int, translate_enabled: bool,
               model: str, headless: bool, wait_captcha: bool) -> dict:
    progress, log = _make_emitter(emit)
    genres = [g.strip() for g in genres if g and g.strip()]
    if not genres:
        raise ValueError("Vui lòng nhập ít nhất một thể loại / từ khoá.")
    scrolls = max(0, min(int(scrolls), config.MAX_SCROLLS))
    model = (model or config.OLLAMA_DEFAULT_MODEL).strip()
    n = len(genres)

    # ---- 1. Đổi từ khoá sang tiếng Trung (0-10%) ----
    progress(1, "Đang dịch từ khoá sang tiếng Trung...", stage="keywords")
    lookup = {translate.strip_accents(k) for k in config.GENRE_MAP}
    needs_ollama = translate_enabled or any(translate.strip_accents(g) not in lookup for g in genres)
    if needs_ollama:
        translate.check_ollama(model)

    pairs: list[tuple[str, str]] = []
    for i, g in enumerate(genres):
        if job.cancel_event.is_set():
            raise JobCancelled()
        cn, source = translate.to_chinese(g, model=model)
        log(f"[{g}] → [{cn}] ({'bảng có sẵn' if source == 'map' else 'model dịch'})")
        pairs.append((g, cn))
        progress(1 + 9 * (i + 1) / n, "Đang dịch từ khoá sang tiếng Trung...", stage="keywords")

    # ---- 2. Cào Zhihu (10-55%) ----
    by_link: dict[str, dict] = {}
    scrape_end = 55 if translate_enabled else 95
    span = (scrape_end - 10) / n
    empty_genres: list[str] = []

    with ZhihuSession(headless=headless, log=log, cancel_event=job.cancel_event) as s:
        if not s.is_logged_in():
            raise ScraperError("Chưa đăng nhập Zhihu. Hãy bấm 'Đăng nhập Zhihu' trước khi tìm.")

        for gi, (g, cn) in enumerate(pairs):
            base = 10 + span * gi
            progress(base, f"Đang cào Zhihu: {g} ({gi + 1}/{n})...", stage="scrape")

            def on_scroll(done, total, _base=base, _g=g):
                progress(_base + span * done / max(total, 1) * 0.9,
                         f"Đang cào Zhihu: {_g} – cuộn {done}/{total}", stage="scrape")

            try:
                items = s.search(cn, scrolls, wait_captcha=wait_captcha, on_scroll=on_scroll)
            except NoResultsError as e:
                log(str(e), "warning")
                empty_genres.append(g)
                items = []

            added = 0
            for it in items:
                key = it.get("link") or it.get("title")
                if key in by_link:  # cùng bài xuất hiện ở nhiều thể loại -> gộp nhãn
                    prev = by_link[key]
                    if g not in prev["genre_vi"].split(", "):
                        prev["genre_vi"] += f", {g}"
                        prev["genre_cn"] += f", {cn}"
                    continue
                it["genre_vi"], it["genre_cn"] = g, cn
                it["title_vi"], it["excerpt_vi"] = "", ""
                by_link[key] = it
                added += 1
            if items:
                log(f"[{g}] lấy được {len(items)} kết quả ({added} mới).", "success")

            if gi < n - 1:
                s._sleep(random.uniform(*config.GENRE_DELAY_RANGE))

    results = list(by_link.values())
    if not results:
        raise NoResultsError(
            "Không lấy được kết quả nào. Nếu trang Zhihu vẫn hiển thị kết quả bình thường thì "
            "selector đã không còn khớp, hãy sửa SELECTORS trong backend/zhihu/config.py."
        )
    results.sort(key=lambda x: x.get("votes", 0), reverse=True)

    # ---- 3. Dịch kết quả sang tiếng Việt (55-95%) ----
    if translate_enabled:
        total = len(results)
        log(f"Bắt đầu dịch {total} kết quả bằng {model}...")
        for i, it in enumerate(results):
            if job.cancel_event.is_set():
                raise JobCancelled()
            progress(55 + 40 * i / total, f"Đang dịch kết quả {i + 1}/{total}...", stage="translate",
                     chunk=it.get("title", "")[:60])
            try:
                it["title_vi"] = translate.to_vietnamese(it.get("title", ""), model=model)
                it["excerpt_vi"] = translate.to_vietnamese(it.get("excerpt", ""), model=model)
            except OllamaError as e:
                log(f"Dừng dịch: {e}. Các kết quả còn lại giữ nguyên tiếng Trung.", "error")
                break

    # ---- 4. Xuất file ----
    progress(97, "Đang xuất CSV/JSON...", stage="export")
    export.export_all(results, job.id)
    if empty_genres:
        log(f"Không có kết quả cho: {', '.join(empty_genres)}", "warning")
    progress(100, f"Hoàn tất: {len(results)} kết quả.", stage="done")
    return {"job_id": job.id, "count": len(results), "results": results}
