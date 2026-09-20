from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

_ALLOWED_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_MAX_ATTACHMENTS = 4
_MAX_BYTES_EACH = 6 * 1024 * 1024

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ATTACHMENTS_DIR = _PROJECT_ROOT / "work" / "attachments"


def attachments_dir() -> Path:
    path = Path(
        os.getenv("WORKBENCH_ATTACHMENTS_DIR") or _DEFAULT_ATTACHMENTS_DIR
    ).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned[:80] or "image"


def validate_attachment_payloads(
    attachments: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    items = [dict(item) for item in attachments]
    if len(items) > _MAX_ATTACHMENTS:
        raise ValueError(f"单次最多上传 {_MAX_ATTACHMENTS} 张图片")

    validated: List[Dict[str, Any]] = []
    for item in items:
        mime_type = str(item.get("mime_type") or "").lower().strip()
        if mime_type not in _ALLOWED_MIME_TO_EXT:
            raise ValueError("仅支持 JPEG、PNG、WebP 图片")

        data_url = str(item.get("data_url") or "")
        expected_prefix = f"data:{mime_type};base64,"
        if not data_url.startswith(expected_prefix):
            raise ValueError("图片数据格式无效")

        encoded = data_url[len(expected_prefix) :]
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("图片 Base64 数据无效") from exc
        if not raw:
            raise ValueError("图片内容为空")
        if len(raw) > _MAX_BYTES_EACH:
            raise ValueError("单张图片不能超过 6MB")

        validated.append(
            {
                "name": _safe_name(str(item.get("name") or "image")),
                "mime_type": mime_type,
                "data_url": data_url,
                "_raw": raw,
            }
        )
    return validated


def image_data_urls(attachments: Iterable[Mapping[str, Any]]) -> List[str]:
    return [item["data_url"] for item in validate_attachment_payloads(attachments)]


def save_attachments(
    attachments: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    validated = validate_attachment_payloads(attachments)
    if not validated:
        return []
    directory = attachments_dir()
    saved: List[Dict[str, Any]] = []

    for item in validated:
        raw = item["_raw"]
        digest = hashlib.sha256(raw).hexdigest()
        ext = _ALLOWED_MIME_TO_EXT[item["mime_type"]]
        filename = f"{digest[:20]}{ext}"
        target = directory / filename
        if not target.exists():
            target.write_bytes(raw)

        saved.append(
            {
                "id": digest[:20],
                "name": item["name"],
                "mime_type": item["mime_type"],
                "size": len(raw),
                "url": f"/attachments/{filename}",
                "sha256": digest,
            }
        )
    return saved
