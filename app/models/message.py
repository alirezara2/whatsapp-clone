from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"  # پیام سیستمی (مثلا "علی به گروه اضافه شد")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # برای پیام سیستمی null

    type: Mapped[MessageType] = mapped_column(SAEnum(MessageType), default=MessageType.TEXT)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # متن یا توضیح فایل
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    sender: Mapped["User"] = relationship("User", back_populates="messages")
    reply_to: Mapped["Message | None"] = relationship(
        "Message", remote_side="Message.id", foreign_keys=[reply_to_id]
    )