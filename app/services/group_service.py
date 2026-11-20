from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import Chat, ChatMember, ChatType, ChatMemberRole
from app.models.message import Message, MessageType
from app.models.user import User


async def create_group(
    db: AsyncSession,
    owner: User,
    name: str,
    description: str | None,
    member_ids: list[int],
    is_public: bool = False,
) -> Chat:
    chat = Chat(
        type=ChatType.GROUP,
        name=name,
        description=description,
        owner_id=owner.id,
        is_public=is_public,
    )
    db.add(chat)
    await db.flush()

    # مالک
    db.add(ChatMember(chat_id=chat.id, user_id=owner.id, role=ChatMemberRole.OWNER))

    # اعضای اولیه (بدون تکرار و بدون خود مالک)
    seen = {owner.id}
    for uid in member_ids:
        if uid in seen:
            continue
        seen.add(uid)
        db.add(ChatMember(chat_id=chat.id, user_id=uid, role=ChatMemberRole.MEMBER))

    # پیام سیستمی
    sys_msg = Message(
        chat_id=chat.id,
        sender_id=None,
        type=MessageType.SYSTEM,
        content=f"گروه «{name}» توسط {owner.name} ساخته شد",
    )
    db.add(sys_msg)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember | None:
    r = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
    )
    return r.scalar_one_or_none()


async def add_system_message(db: AsyncSession, chat_id: int, text: str):
    msg = Message(chat_id=chat_id, sender_id=None, type=MessageType.SYSTEM, content=text)
    db.add(msg)
    await db.commit()
    return msg


async def load_group(db: AsyncSession, chat_id: int) -> Chat | None:
    r = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.type == ChatType.GROUP)
        .options(selectinload(Chat.members).selectinload(ChatMember.user))
    )
    return r.scalar_one_or_none()