from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserPublic
from app.utils.deps import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
async def list_users(
    q: str | None = Query(None, description="جستجو در نام/شماره/یوزرنیم"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    stmt = (
        select(User)
        .where(User.is_active.is_(True), User.id != current.id)
        .order_by(User.name)
        .limit(limit)
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                User.phone.ilike(pattern),
                User.name.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    result = await db.execute(stmt)
    return [UserPublic.model_validate(u) for u in result.scalars().all()]


@router.get("/search", response_model=list[UserPublic])
async def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pattern = f"%{q}%"
    stmt = (
        select(User)
        .where(
            User.is_active.is_(True),
            or_(
                User.phone.ilike(pattern),
                User.name.ilike(pattern),
                User.username.ilike(pattern),
            ),
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [UserPublic.model_validate(u) for u in result.scalars().all()]


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "کاربر یافت نشد")
    return UserPublic.model_validate(user)