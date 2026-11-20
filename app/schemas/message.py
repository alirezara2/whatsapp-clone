from datetime import datetime
from pydantic import BaseModel, Field
from app.models.message import MessageType
from app.schemas.user import UserPublic


class MessageCreate(BaseModel):
    type: MessageType = MessageType.TEXT
    content: str | None = Field(None, max_length=5000)
    file_url: str | None = None
    file_name: str | None = None
    reply_to_id: int | None = None

    def validate_content(self):
        if self.type == MessageType.TEXT and not self.content:
            raise ValueError("متن پیام نمیتونه خالی باشه")
        return self


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessagePublic(BaseModel):
    id: int
    chat_id: int
    sender_id: int | None = None
    sender: UserPublic | None = None
    type: MessageType
    content: str | None = None
    file_url: str | None = None
    file_name: str | None = None
    reply_to_id: int | None = None
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}