import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings


ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_DIR = Path(settings.UPLOAD_DIR) / "avatars"
MESSAGE_DIR = Path(settings.UPLOAD_DIR) / "messages"

MAX_MESSAGE_SIZE = 20 * 1024 * 1024  # 20MB

ALLOWED_MESSAGE_TYPES = {
    # عکس
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    # فیلم
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
    "video/x-msvideo": "video",
    # صدا
    "audio/mpeg": "audio",
    "audio/ogg": "audio",
    "audio/wav": "audio",
    "audio/webm": "audio",
    # فایل
    "application/pdf": "file",
    "application/zip": "file",
    "application/x-zip-compressed": "file",
    "application/msword": "file",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "file",
    "application/vnd.ms-excel": "file",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "file",
    "text/plain": "file",
    "application/octet-stream": "file",
}


def _ensure_dirs():
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    MESSAGE_DIR.mkdir(parents=True, exist_ok=True)


async def save_avatar(file: UploadFile) -> str:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(400, "فرمت تصویر مجاز نیست (jpeg/png/webp)")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "حجم عکس بیش از حد مجاز است (5MB)")

    _ensure_dirs()
    ext = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = AVATAR_DIR / filename
    filepath.write_bytes(contents)

    return f"/static/uploads/avatars/{filename}"


async def save_message_file(file: UploadFile) -> tuple[str, str, str]:
    """
    فایل پیام رو ذخیره میکنه.
    برمیگردونه: (url, original_filename, message_type)
    """
    mtype = ALLOWED_MESSAGE_TYPES.get(file.content_type or "")
    if not mtype:
        raise HTTPException(400, f"نوع فایل مجاز نیست: {file.content_type}")

    contents = await file.read()
    if len(contents) > MAX_MESSAGE_SIZE:
        raise HTTPException(413, "حجم فایل بیش از حد مجاز است (20MB)")

    _ensure_dirs()
    original = Path(file.filename or "file")
    ext = original.suffix.lower() or ".bin"
    safe_stem = "".join(c for c in original.stem if c.isalnum() or c in "-_")[:40] or "file"
    filename = f"{uuid.uuid4().hex}_{safe_stem}{ext}"
    filepath = MESSAGE_DIR / filename
    filepath.write_bytes(contents)

    url = f"/static/uploads/messages/{filename}"
    return url, original.name, mtype


def delete_avatar(avatar_url: str | None):
    if not avatar_url:
        return
    relative = avatar_url.lstrip("/")
    path = Path(relative)
    if path.exists() and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass