from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMember, ChatType, ChatMemberRole
from app.schemas.chat import ChatPublic, ChatMemberPublic
from app.schemas.channel import ChannelCreate, ChannelUpdate, AddChannelAdmin
from app.schemas.message import MessagePublic
from app.utils.deps import get_current_user
from app.services import channel_service, message_service
from app.services.upload import save_avatar, delete_avatar


router = APIRouter(prefix="/channels", tags=["channels"])


def _to_chat_public(c: Chat, last, unread: int) -> ChatPublic:
    return ChatPublic(
        id=c.id, type=c.type, name=c.name, description=c.description, avatar=c.avatar,
        owner_id=c.owner_id, is_public=c.is_public,
        created_at=c.created_at, updated_at=c.updated_at,
        members=[
            ChatMemberPublic(
                user_id=m.user_id, role=m.role, joined_at=m.joined_at,
                is_muted=m.is_muted, user=m.user,
            )
            for m in c.members
        ],
        last_message=MessagePublic.model_validate(last) if last else None,
        unread_count=unread,
    )


@router.post("", response_model=ChatPublic, status_code=status.HTTP_201_CREATED)
async def create_channel(
    payload: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    chat = await channel_service.create_channel(
        db, owner=current, name=payload.name,
        description=payload.description, is_public=payload.is_public,
    )
    full = await channel_service.load_channel(db, chat.id)
    last = await message_service.get_last_message(db, chat.id)
    return _to_chat_public(full, last, 0)


@router.get("/public", response_model=list[ChatPublic])
async def list_public_channels(
    q: str | None = Query(None, description="جستجو در نام"),
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    stmt = (
        select(Chat)
        .where(Chat.type == ChatType.CHANNEL, Chat.is_public.is_(True))
        .options(selectinload(Chat.members).selectinload(ChatMember.user))
        .limit(limit)
    )
    if q:
        stmt = stmt.where(Chat.name.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    chats = result.scalars().unique().all()
    out = []
    for c in chats:
        last = await message_service.get_last_message(db, c.id)
        unread = await message_service.get_unread_count(db, c.id, current.id)
        out.append(_to_chat_public(c, last, unread))
    return out


@router.get("/{channel_id}", response_model=ChatPublic)
async def get_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await channel_service.get_member(db, channel_id, current.id)
    if not member:
        raise HTTPException(403, "ابتدا عضو کانال شوید")
    c = await channel_service.load_channel(db, channel_id)
    if not c:
        raise HTTPException(404, "کانال یافت نشد")
    last = await message_service.get_last_message(db, channel_id)
    unread = await message_service.get_unread_count(db, channel_id, current.id)
    return _to_chat_public(c, last, unread)


@router.patch("/{channel_id}", response_model=ChatPublic)
async def update_channel(
    channel_id: int,
    payload: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    m = await channel_service.get_member(db, channel_id, current.id)
    if not m or m.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
        raise HTTPException(403, "فقط ادمین/مالک میتونه ویرایش کنه")
    c = await channel_service.load_channel(db, channel_id)
    if not c:
        raise HTTPException(404, "کانال یافت نشد")
    if payload.name is not None:
        c.name = payload.name
    if payload.description is not None:
        c.description = payload.description
    if payload.is_public is not None:
        c.is_public = payload.is_public
    await db.commit()
    await db.refresh(c)
    last = await message_service.get_last_message(db, channel_id)
    unread = await message_service.get_unread_count(db, channel_id, current.id)
    return _to_chat_public(c, last, unread)


@router.post("/{channel_id}/avatar", response_model=ChatPublic)
async def upload_channel_avatar(
    channel_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    m = await channel_service.get_member(db, channel_id, current.id)
    if not m or m.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
        raise HTTPException(403, "فقط ادمین/مالک")
    c = await channel_service.load_channel(db, channel_id)
    if not c:
        raise HTTPException(404, "کانال یافت نشد")
    delete_avatar(c.avatar)
    c.avatar = await save_avatar(file)
    await db.commit()
    await db.refresh(c)
    last = await message_service.get_last_message(db, channel_id)
    unread = await message_service.get_unread_count(db, channel_id, current.id)
    return _to_chat_public(c, last, unread)


@router.post("/{channel_id}/subscribe", response_model=ChatPublic)
async def subscribe(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    c = await channel_service.load_channel(db, channel_id)
    if not c:
        raise HTTPException(404, "کانال یافت نشد")
    if await channel_service.get_member(db, channel_id, current.id):
        raise HTTPException(400, "قبلاً عضو هستید")
    if not c.is_public:
        raise HTTPException(403, "این کانال خصوصی است")

    db.add(ChatMember(chat_id=channel_id, user_id=current.id, role=ChatMemberRole.MEMBER))
    await channel_service.add_system_message(db, channel_id, f"{current.name} عضو کانال شد")
    await db.commit()

    c = await channel_service.load_channel(db, channel_id)
    last = await message_service.get_last_message(db, channel_id)
    return _to_chat_public(c, last, 0)


@router.post("/{channel_id}/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    m = await channel_service.get_member(db, channel_id, current.id)
    if not m:
        raise HTTPException(404, "عضو نیستید")
    if m.role == ChatMemberRole.OWNER:
        raise HTTPException(400, "مالک نمیتونه خارج بشه")
    await db.delete(m)
    await channel_service.add_system_message(db, channel_id, f"{current.name} لغو عضویت کرد")
    await db.commit()
    return None


@router.post("/{channel_id}/admins", response_model=ChatPublic)
async def add_admin(
    channel_id: int,
    payload: AddChannelAdmin,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    me = await channel_service.get_member(db, channel_id, current.id)
    if not me or me.role != ChatMemberRole.OWNER:
        raise HTTPException(403, "فقط مالک میتونه ادمین اضافه کنه")
    target = await channel_service.get_member(db, channel_id, payload.user_id)
    if not target:
        raise HTTPException(404, "کاربر عضو کانال نیست، اول باید subscribe کنه")
    if target.role == ChatMemberRole.OWNER:
        raise HTTPException(400, "مالک قابل تغییر نیست")
    target.role = ChatMemberRole.ADMIN
    await db.commit()

    c = await channel_service.load_channel(db, channel_id)
    last = await message_service.get_last_message(db, channel_id)
    return _to_chat_public(c, last, 0)


@router.delete("/{channel_id}/admins/{user_id}", response_model=ChatPublic)
async def remove_admin(
    channel_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    me = await channel_service.get_member(db, channel_id, current.id)
    if not me or me.role != ChatMemberRole.OWNER:
        raise HTTPException(403, "فقط مالک")
    target = await channel_service.get_member(db, channel_id, user_id)
    if not target or target.role != ChatMemberRole.ADMIN:
        raise HTTPException(404, "کاربر ادمین نیست")
    target.role = ChatMemberRole.MEMBER
    await db.commit()

    c = await channel_service.load_channel(db, channel_id)
    last = await message_service.get_last_message(db, channel_id)
    return _to_chat_public(c, last, 0)