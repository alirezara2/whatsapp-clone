from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(None, max_length=500)
    member_ids: list[int] = Field(default_factory=list, description="آیدی کاربران اولیه")
    is_public: bool = False


class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = Field(None, max_length=500)
    is_public: bool | None = None


class AddMembers(BaseModel):
    user_ids: list[int] = Field(..., min_length=1)


class ChangeRole(BaseModel):
    role: str = Field(..., pattern="^(member|admin)$")