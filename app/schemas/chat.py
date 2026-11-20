from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.chat import ChatType, ChatMemberRole
from app.schemas.user import UserPublic
from app.schemas.message import MessagePublic


class ChatMemberPublic(BaseModel):
    user_id: int
    role: ChatMemberRole
    joined_at: datetime
    is_muted: bool = False
    user: UserPublic

    model_config = ConfigDict(from_attributes=True)


class ChatPublic(BaseModel):
    id: int
    type: ChatType
    name: str | None = None
    description: str | None = None
    avatar: str | None = None
    owner_id: int | None = None
    is_public: bool = False
    created_at: datetime
    updated_at: datetime
    members: list[ChatMemberPublic] = []
    last_message: MessagePublic | None = None
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)