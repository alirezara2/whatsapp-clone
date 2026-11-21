from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.message import MessageType
from app.schemas.user import UserPublic


class MessageCreate(BaseModel):
    type: MessageType = MessageType.TEXT
    content: str | None = Field(None, max_length=5000)
    file_url: str | None = None
    file_name: str | None = None
    reply_to_id: int | None = None


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
    is_edited: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)