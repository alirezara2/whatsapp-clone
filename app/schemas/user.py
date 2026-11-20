from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


PHONE_REGEX = re.compile(r"^\+?[1-9]\d{9,14}$")


class UserBase(BaseModel):
    phone: str = Field(..., examples=["+989121234567"])
    name: str = Field(..., min_length=2, max_length=100)
    bio: str | None = Field(None, max_length=200)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_REGEX.match(v):
            raise ValueError("شماره تماس معتبر نیست. مثال: +989121234567")
        return v


class UserLogin(BaseModel):
    phone: str
    password: str


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    bio: str | None = Field(None, max_length=200)
    username: str | None = Field(None, min_length=3, max_length=50)


class UserPublic(BaseModel):
    id: int
    phone: str
    name: str
    username: str | None = None
    bio: str | None = None
    avatar: str | None = None
    last_seen: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserMe(UserPublic):
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)