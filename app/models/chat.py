from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class Chat(Base):
    """
    یک Chat میتونه private (چت دوطرفه)، group، یا channel باشه.
    برای private، name خالیه و اعضا از ChatMember میان.
    """
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[ChatType] = mapped_column(SAEnum(ChatType), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)  # برای group/channel
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)

    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # مالک گروه/کانال

    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # برای کانال/گروه عمومی

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # روابط
    members: Mapped[list["ChatMember"]] = relationship(
        "ChatMember", back_populates="chat", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )


class ChatMemberRole(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


class ChatMember(Base):
    __tablename__ = "chat_members"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ChatMemberRole] = mapped_column(SAEnum(ChatMemberRole), default=ChatMemberRole.MEMBER)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_read_message_id: Mapped[int | None] = mapped_column(nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="chat_memberships")