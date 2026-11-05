from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ProfileResponse(BaseModel):
    id: str
    avatar_url: str = Field(default="", serialization_alias="avatarUrl", validation_alias="avatarUrl")
    name: str
    username: str = ""
    university: str = ""
    batch: Optional[int] = None
    role: str = Field(default="", serialization_alias="role", validation_alias="role")
    role_emoji: str = Field(default="", serialization_alias="roleEmoji", validation_alias="roleEmoji")
    bio: str = ""
    location: str = ""

    model_config = ConfigDict(populate_by_name=True)

class ProfileUpdateRequest(BaseModel):
    avatar_url: Optional[str] = Field(default=None, alias="avatarUrl")
    name: Optional[str] = None
    username: Optional[str] = None
    university: Optional[str] = None
    batch: Optional[int] = None
    role: Optional[str] = None
    role_emoji: Optional[str] = Field(default=None, alias="roleEmoji")
    bio: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
