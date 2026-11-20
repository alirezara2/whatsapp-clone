from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import Chat, ChatMember
from app.models.message import Message
from app.models.user import User


async def is_member(db: AsyncSession, chat_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


async def get_chat_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember | None:
    result = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_message(
    db: AsyncSession,
    chat_id: int,
    sender_id: int,
    content: str | None,
    msg_type=None,
    file_url: str | None = None,
    file_name: str | None = None,
    reply_to_id: int | None = None,
) -> Message:
    from app.models.message import MessageType
    msg = Message(
        chat_id=chat_id,
        sender_id=sender_id,
        type=msg_type or MessageType.TEXT,
        content=content,
        file_url=file_url,
        file_name=file_name,
        reply_to_id=reply_to_id,
    )
    db.add(msg)
    await db.commit()
    result = await db.execute(
        select(Message).where(Message.id == msg.id).options(selectinload(Message.sender))
    )
    return result.scalar_one()


async def get_messages(
    db: AsyncSession, chat_id: int, before_id: int | None = None, limit: int = 30
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .options(selectinload(Message.sender))
        .order_by(Message.id.desc())
        .limit(limit)
    )
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    result = await db.execute(stmt)
    msgs = list(result.scalars().all())
    msgs.reverse()  # قدیمی → جدید
    return msgs


async def get_last_message(db: AsyncSession, chat_id: int) -> Message | None:
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id, Message.is_deleted.is_(False))
        .options(selectinload(Message.sender))
        .order_by(Message.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_unread_count(db: AsyncSession, chat_id: int, user_id: int) -> int:
    member = await get_chat_member(db, chat_id, user_id)
    if not member:
        return 0
    last_read = member.last_read_message_id or 0
    result = await db.execute(
        select(func.count(Message.id)).where(
            Message.chat_id == chat_id,
            Message.id > last_read,
            Message.sender_id != user_id,
            Message.is_deleted.is_(False),
        )
    )
    return result.scalar_one()