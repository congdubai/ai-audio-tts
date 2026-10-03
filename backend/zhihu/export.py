"""Xuất kết quả ra JSON / CSV."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import config

FIELDS = [
    "genre_vi", "genre_cn", "votes",
    "title", "title_vi",
    "excerpt", "excerpt_vi",
    "link",
]


def _path(job_id: str, ext: str) -> Path:
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return config.OUTPUTS_DIR / f"zhihu_{job_id}.{ext}"


def to_json(results: list[dict], job_id: str) -> Path:
    path = _path(job_id, "json")
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def to_csv(results: list[dict], job_id: str) -> Path:
    path = _path(job_id, "csv")
    # utf-8-sig để Excel hiển thị đúng tiếng Việt / tiếng Trung
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in results:
            w.writerow({k: row.get(k, "") for k in FIELDS})
    return path


def export_all(results: list[dict], job_id: str) -> dict[str, Path]:
    return {"json": to_json(results, job_id), "csv": to_csv(results, job_id)}


def get_export_path(job_id: str, fmt: str) -> Path | None:
    if fmt not in ("json", "csv") or not job_id.replace("-", "").isalnum():
        return None
    path = config.OUTPUTS_DIR / f"zhihu_{job_id}.{fmt}"
    return path if path.exists() else None
