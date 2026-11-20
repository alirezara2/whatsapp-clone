from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import Chat, ChatMember, ChatType, ChatMemberRole
from app.models.message import Message, MessageType
from app.models.user import User


async def create_channel(
    db: AsyncSession, owner: User, name: str, description: str | None, is_public: bool
) -> Chat:
    chat = Chat(
        type=ChatType.CHANNEL,
        name=name,
        description=description,
        owner_id=owner.id,
        is_public=is_public,
    )
    db.add(chat)
    await db.flush()

    db.add(ChatMember(chat_id=chat.id, user_id=owner.id, role=ChatMemberRole.OWNER))

    msg = Message(
        chat_id=chat.id, sender_id=None, type=MessageType.SYSTEM,
        content=f"کانال «{name}» توسط {owner.name} ساخته شد",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember | None:
    r = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
    )
    return r.scalar_one_or_none()


async def load_channel(db: AsyncSession, chat_id: int) -> Chat | None:
    r = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.type == ChatType.CHANNEL)
        .options(selectinload(Chat.members).selectinload(ChatMember.user))
    )
    return r.scalar_one_or_none()


async def can_post(db: AsyncSession, chat_id: int, user_id: int) -> bool:
    m = await get_member(db, chat_id, user_id)
    return bool(m and m.role in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER))


async def add_system_message(db: AsyncSession, chat_id: int, text: str):
    msg = Message(chat_id=chat_id, sender_id=None, type=MessageType.SYSTEM, content=text)
    db.add(msg)
    await db.commit()
    return msg