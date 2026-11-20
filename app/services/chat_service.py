from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import Chat, ChatMember, ChatType, ChatMemberRole


async def get_or_create_private_chat(db: AsyncSession, user_a_id: int, user_b_id: int) -> Chat:
    if user_a_id == user_b_id:
        raise ValueError("نمیتونی با خودت چت خصوصی بسازی")

    sub_a = (
        select(ChatMember.chat_id)
        .join(Chat, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == user_a_id, Chat.type == ChatType.PRIVATE)
    )
    sub_b = select(ChatMember.chat_id).where(ChatMember.user_id == user_b_id)
    stmt = (
        select(Chat)
        .where(Chat.id.in_(sub_a), Chat.id.in_(sub_b))
        .options(selectinload(Chat.members))
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing and len(existing.members) == 2:
        return existing

    chat = Chat(type=ChatType.PRIVATE)
    db.add(chat)
    await db.flush()

    db.add_all([
        ChatMember(chat_id=chat.id, user_id=user_a_id, role=ChatMemberRole.MEMBER),
        ChatMember(chat_id=chat.id, user_id=user_b_id, role=ChatMemberRole.MEMBER),
    ])
    await db.commit()
    await db.refresh(chat)
    return chat


async def find_private_chat_id(db: AsyncSession, user_a_id: int, user_b_id: int) -> int | None:
    sub_a = (
        select(ChatMember.chat_id)
        .join(Chat, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == user_a_id, Chat.type == ChatType.PRIVATE)
    )
    sub_b = select(ChatMember.chat_id).where(ChatMember.user_id == user_b_id)
    stmt = select(Chat.id).where(Chat.id.in_(sub_a), Chat.id.in_(sub_b))
    result = await db.execute(stmt)
    return result.scalars().first()