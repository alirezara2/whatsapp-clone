from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserPublic, UserMe
from app.schemas.auth import TokenWithUser
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.deps import get_current_user
from app.services.upload import save_avatar


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenWithUser, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # چک تکراری بودن شماره
    exists = await db.execute(select(User).where(User.phone == payload.phone))
    if exists.scalar_one_or_none():
        raise HTTPException(400, "این شماره تماس قبلاً ثبت شده است")

    user = User(
        phone=payload.phone,
        name=payload.name,
        bio=payload.bio,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenWithUser(
        access_token=token,
        user=UserPublic.model_validate(user),
    )


@router.post("/login", response_model=TokenWithUser)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "شماره تماس یا رمز عبور اشتباه است")
    if not user.is_active:
        raise HTTPException(403, "حساب غیرفعال است")

    token = create_access_token({"sub": str(user.id)})
    return TokenWithUser(
        access_token=token,
        user=UserPublic.model_validate(user),
    )


@router.get("/me", response_model=UserMe)
async def me(current: User = Depends(get_current_user)):
    return UserMe.model_validate(current)


@router.post("/me/avatar", response_model=UserMe)
async def upload_avatar(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # پاک کردن عکس قبلی (اختیاری)
    from app.services.upload import delete_avatar
    delete_avatar(current.avatar)

    url = await save_avatar(file)
    current.avatar = url
    await db.commit()
    await db.refresh(current)
    return UserMe.model_validate(current)


@router.patch("/me", response_model=UserMe)
async def update_me(
    payload: dict,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.user import UserUpdate
    data = UserUpdate(**payload)
    if data.name is not None:
        current.name = data.name
    if data.bio is not None:
        current.bio = data.bio
    if data.username is not None:
        # چک تکراری
        dup = await db.execute(
            select(User).where(User.username == data.username, User.id != current.id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(400, "این نام کاربری قبلاً گرفته شده")
        current.username = data.username
    await db.commit()
    await db.refresh(current)
    return UserMe.model_validate(current)