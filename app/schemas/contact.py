from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.user import UserPublic


class ContactCreate(BaseModel):
    phone: str = Field(..., examples=["+989121234567"])
    alias: str | None = Field(None, max_length=100)


class ContactPublic(BaseModel):
    id: int
    alias: str | None = None
    created_at: datetime
    contact: UserPublic  # اطلاعات کاربر مخاطب

    model_config = {"from_attributes": True}


class ContactWithChat(BaseModel):
    """برای لیست مخاطبین همراه با شناسه چت خصوصی (اگه وجود داشت)"""
    id: int
    alias: str | None = None
    created_at: datetime
    contact: UserPublic
    chat_id: int | None = None

    model_config = {"from_attributes": True}