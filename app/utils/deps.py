from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token


security_scheme = HTTPBearer(auto_error=False)


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """اگه datetime naive بود، aware UTC کن."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="احراز هویت نامعتبر است",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise cred_exc

    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise cred_exc

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise cred_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise cred_exc

    # آپدیت last_seen — با احتیاط timezone
    try:
        now = datetime.now(timezone.utc)
        last = _ensure_aware(user.last_seen)
        if last is None or (now - last) > timedelta(seconds=60):
            user.last_seen = now
            await db.commit()
    except Exception:
        pass

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()