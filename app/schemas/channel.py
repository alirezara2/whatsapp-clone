from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(None, max_length=500)
    is_public: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = Field(None, max_length=500)
    is_public: bool | None = None


class AddChannelAdmin(BaseModel):
    user_id: int