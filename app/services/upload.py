import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings


ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_DIR = Path(settings.UPLOAD_DIR) / "avatars"


def _ensure_dir():
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)


async def save_avatar(file: UploadFile) -> str:
    """
    فایل عکس پروفایل رو ذخیره میکنه و مسیر نسبی برای استفاده در <img src> برمیگردونه.
    """
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(400, "فرمت تصویر مجاز نیست (jpeg/png/webp)")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "حجم عکس بیش از حد مجاز است (5MB)")

    _ensure_dir()
    ext = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = AVATAR_DIR / filename
    filepath.write_bytes(contents)

    # مسیر قابل استفاده در URL
    return f"/static/uploads/avatars/{filename}"


def delete_avatar(avatar_url: str | None):
    if not avatar_url:
        return
    # /static/uploads/avatars/xxx.jpg → app/static/uploads/avatars/xxx.jpg
    relative = avatar_url.lstrip("/")
    path = Path(relative)
    if path.exists() and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass