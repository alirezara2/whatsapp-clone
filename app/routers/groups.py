from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMember, ChatType, ChatMemberRole
from app.schemas.chat import ChatPublic, ChatMemberPublic
from app.schemas.group import GroupCreate, GroupUpdate, AddMembers, ChangeRole
from app.schemas.message import MessagePublic
from app.utils.deps import get_current_user
from app.services import group_service, message_service
from app.services.upload import save_avatar, delete_avatar


router = APIRouter(prefix="/groups", tags=["groups"])


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
async def create_group(
    payload: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    chat = await group_service.create_group(
        db, owner=current, name=payload.name, description=payload.description,
        member_ids=payload.member_ids, is_public=payload.is_public,
    )
    full = await group_service.load_group(db, chat.id)
    last = await message_service.get_last_message(db, chat.id)
    unread = await message_service.get_unread_count(db, chat.id, current.id)
    return _to_chat_public(full, last, unread)


@router.get("/{group_id}", response_model=ChatPublic)
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await group_service.get_member(db, group_id, current.id)
    if not member:
        raise HTTPException(403, "شما عضو این گروه نیستید")
    g = await group_service.load_group(db, group_id)
    if not g:
        raise HTTPException(404, "گروه یافت نشد")
    last = await message_service.get_last_message(db, group_id)
    unread = await message_service.get_unread_count(db, group_id, current.id)
    return _to_chat_public(g, last, unread)


@router.patch("/{group_id}", response_model=ChatPublic)
async def update_group(
    group_id: int,
    payload: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await group_service.get_member(db, group_id, current.id)
    if not member or member.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
        raise HTTPException(403, "فقط ادمین/مالک میتونه ویرایش کنه")
    g = await group_service.load_group(db, group_id)
    if not g:
        raise HTTPException(404, "گروه یافت نشد")
    if payload.name is not None:
        g.name = payload.name
    if payload.description is not None:
        g.description = payload.description
    if payload.is_public is not None:
        g.is_public = payload.is_public
    await db.commit()
    await db.refresh(g)
    last = await message_service.get_last_message(db, group_id)
    unread = await message_service.get_unread_count(db, group_id, current.id)
    return _to_chat_public(g, last, unread)


@router.post("/{group_id}/avatar", response_model=ChatPublic)
async def upload_group_avatar(
    group_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await group_service.get_member(db, group_id, current.id)
    if not member or member.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
        raise HTTPException(403, "فقط ادمین/مالک میتونه عکس بذاره")
    g = await group_service.load_group(db, group_id)
    if not g:
        raise HTTPException(404, "گروه یافت نشد")
    delete_avatar(g.avatar)
    g.avatar = await save_avatar(file)
    await db.commit()
    await db.refresh(g)
    last = await message_service.get_last_message(db, group_id)
    unread = await message_service.get_unread_count(db, group_id, current.id)
    return _to_chat_public(g, last, unread)


@router.post("/{group_id}/members", response_model=ChatPublic)
async def add_members(
    group_id: int,
    payload: AddMembers,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await group_service.get_member(db, group_id, current.id)
    if not member or member.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
        raise HTTPException(403, "فقط ادمین/مالک میتونه عضو اضافه کنه")
    g = await group_service.load_group(db, group_id)
    if not g:
        raise HTTPException(404, "گروه یافت نشد")

    existing = {m.user_id for m in g.members}
    added_names = []
    for uid in payload.user_ids:
        if uid in existing:
            continue
        # چک وجود کاربر
        r = await db.execute(select(User).where(User.id == uid, User.is_active.is_(True)))
        u = r.scalar_one_or_none()
        if not u:
            continue
        db.add(ChatMember(chat_id=group_id, user_id=uid, role=ChatMemberRole.MEMBER))
        added_names.append(u.name)

    if added_names:
        await group_service.add_system_message(
            db, group_id, f"{current.name} افزود: {', '.join(added_names)}"
        )
    await db.commit()

    g = await group_service.load_group(db, group_id)
    last = await message_service.get_last_message(db, group_id)
    unread = await message_service.get_unread_count(db, group_id, current.id)
    return _to_chat_public(g, last, unread)


@router.delete("/{group_id}/members/{user_id}", response_model=ChatPublic)
async def remove_member(
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    me = await group_service.get_member(db, group_id, current.id)
    if not me or me.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
        raise HTTPException(403, "فقط ادمین/مالک میتونه حذف کنه")
    target = await group_service.get_member(db, group_id, user_id)
    if not target:
        raise HTTPException(404, "کاربر عضو این گروه نیست")
    if target.role == ChatMemberRole.OWNER:
        raise HTTPException(400, "مالک قابل حذف نیست")
    r = await db.execute(select(User).where(User.id == user_id))
    u = r.scalar_one_or_none()
    await db.delete(target)
    if u:
        await group_service.add_system_message(db, group_id, f"{current.name} حذف کرد: {u.name}")
    await db.commit()

    g = await group_service.load_group(db, group_id)
    last = await message_service.get_last_message(db, group_id)
    unread = await message_service.get_unread_count(db, group_id, current.id)
    return _to_chat_public(g, last, unread)


@router.post("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    member = await group_service.get_member(db, group_id, current.id)
    if not member:
        raise HTTPException(404, "شما عضو این گروه نیستید")
    if member.role == ChatMemberRole.OWNER:
        raise HTTPException(400, "مالک باید اول گروه رو حذف یا مالکیت رو انتقال بده")
    await db.delete(member)
    await group_service.add_system_message(db, group_id, f"{current.name} از گروه خارج شد")
    await db.commit()
    return None


@router.patch("/{group_id}/members/{user_id}/role", response_model=ChatPublic)
async def change_role(
    group_id: int,
    user_id: int,
    payload: ChangeRole,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    me = await group_service.get_member(db, group_id, current.id)
    if not me or me.role != ChatMemberRole.OWNER:
        raise HTTPException(403, "فقط مالک میتونه نقش تغییر بده")
    target = await group_service.get_member(db, group_id, user_id)
    if not target:
        raise HTTPException(404, "کاربر عضو این گروه نیست")
    if target.role == ChatMemberRole.OWNER:
        raise HTTPException(400, "نقش مالک قابل تغییر نیست")
    target.role = ChatMemberRole.ADMIN if payload.role == "admin" else ChatMemberRole.MEMBER
    await db.commit()

    g = await group_service.load_group(db, group_id)
    last = await message_service.get_last_message(db, group_id)
    unread = await message_service.get_unread_count(db, group_id, current.id)
    return _to_chat_public(g, last, unread)