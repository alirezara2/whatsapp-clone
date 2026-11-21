from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMember
from app.models.message import Message
from app.schemas.chat import ChatPublic, ChatMemberPublic
from app.schemas.message import MessagePublic, MessageUpdate
from app.schemas.user import UserPublic
from app.utils.deps import get_current_user
from app.services import message_service
from app.services.chat_service import get_or_create_private_chat
from app.services.upload import save_message_file


router = APIRouter(prefix="/chats", tags=["chats"])


def _build_chat_public(c: Chat, last, unread: int) -> ChatPublic:
    members_out = []
    for m in c.members:
        members_out.append(
            ChatMemberPublic(
                user_id=m.user_id,
                role=m.role,
                joined_at=m.joined_at,
                is_muted=m.is_muted,
                user=UserPublic.model_validate(m.user),
            )
        )
    return ChatPublic(
        id=c.id,
        type=c.type,
        name=c.name,
        description=c.description,
        avatar=c.avatar,
        owner_id=c.owner_id,
        is_public=c.is_public,
        created_at=c.created_at,
        updated_at=c.updated_at,
        members=members_out,
        last_message=MessagePublic.model_validate(last) if last else None,
        unread_count=unread,
    )


@router.get("", response_model=list[ChatPublic])
async def list_chats(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    stmt = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == current.id)
        .options(selectinload(Chat.members).selectinload(ChatMember.user))
    )
    result = await db.execute(stmt)
    chats = result.scalars().unique().all()

    out = []
    for c in chats:
        last = await message_service.get_last_message(db, c.id)
        unread = await message_service.get_unread_count(db, c.id, current.id)
        out.append(_build_chat_public(c, last, unread))

    out.sort(
        key=lambda x: x.last_message.created_at if x.last_message else x.created_at,
        reverse=True,
    )
    return out


@router.post("/private/{user_id}", response_model=ChatPublic)
async def open_private_chat(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if user_id == current.id:
        raise HTTPException(400, "نمیتونی با خودت چت کنی")

    target = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not target.scalar_one_or_none():
        raise HTTPException(404, "کاربر یافت نشد")

    chat = await get_or_create_private_chat(db, current.id, user_id)

    stmt = (
        select(Chat)
        .where(Chat.id == chat.id)
        .options(selectinload(Chat.members).selectinload(ChatMember.user))
    )
    result = await db.execute(stmt)
    c = result.scalar_one()

    last = await message_service.get_last_message(db, c.id)
    unread = await message_service.get_unread_count(db, c.id, current.id)
    return _build_chat_public(c, last, unread)


@router.post("/{chat_id}/upload", response_model=MessagePublic)
async def upload_message_file(
    chat_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """آپلود عکس/فیلم/فایل و ساخت پیام + broadcast."""
    if not await message_service.is_member(db, chat_id, current.id):
        raise HTTPException(403, "شما عضو این چت نیستید")

    url, original_name, mtype = await save_message_file(file)

    from app.models.message import MessageType
    msg = await message_service.create_message(
        db,
        chat_id=chat_id,
        sender_id=current.id,
        content=None,
        msg_type=MessageType(mtype),
        file_url=url,
        file_name=original_name,
    )
    payload = MessagePublic.model_validate(msg)

    # broadcast از طریق WebSocket
    from app.services.ws_manager import manager
    await manager.broadcast(
        chat_id,
        {"event": "new_message", "message": payload.model_dump(mode="json")},
    )
    return payload


@router.get("/{chat_id}", response_model=ChatPublic)
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not await message_service.is_member(db, chat_id, current.id):
        raise HTTPException(403, "شما عضو این چت نیستید")
    stmt = (
        select(Chat)
        .where(Chat.id == chat_id)
        .options(selectinload(Chat.members).selectinload(ChatMember.user))
    )
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "چت یافت نشد")
    last = await message_service.get_last_message(db, c.id)
    unread = await message_service.get_unread_count(db, c.id, current.id)
    return _build_chat_public(c, last, unread)


@router.get("/{chat_id}/messages", response_model=list[MessagePublic])
async def get_messages(
    chat_id: int,
    before_id: int | None = Query(None),
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not await message_service.is_member(db, chat_id, current.id):
        raise HTTPException(403, "شما عضو این چت نیستید")
    msgs = await message_service.get_messages(db, chat_id, before_id=before_id, limit=limit)
    return [MessagePublic.model_validate(m) for m in msgs]


@router.patch("/messages/{message_id}", response_model=MessagePublic)
async def edit_message(
    message_id: int,
    payload: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Message).where(Message.id == message_id).options(selectinload(Message.sender))
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "پیام یافت نشد")
    if msg.sender_id != current.id:
        raise HTTPException(403, "فقط فرستنده میتونه ویرایش کنه")
    if msg.is_deleted:
        raise HTTPException(400, "پیام حذف شده قابل ویرایش نیست")
    msg.content = payload.content
    msg.is_edited = True
    await db.commit()
    await db.refresh(msg)
    return MessagePublic.model_validate(msg)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "پیام یافت نشد")
    if msg.sender_id != current.id:
        raise HTTPException(403, "فقط فرستنده میتونه حذف کنه")
    msg.is_deleted = True
    msg.content = None
    msg.file_url = None
    msg.file_name = None
    await db.commit()
    return None


@router.post("/{chat_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await message_service.get_chat_member(db, chat_id, current.id)
    if not member:
        raise HTTPException(403, "شما عضو این چت نیستید")
    last = await message_service.get_last_message(db, chat_id)
    if last:
        member.last_read_message_id = last.id
        await db.commit()
    return None