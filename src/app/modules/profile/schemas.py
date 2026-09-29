from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ProfileResponse(BaseModel):
    # `id` dipakai frontend untuk menandai pesan miliknya sendiri. Tanpa ini
    # frontend harus memakai id hardcoded "me" yang tidak pernah sama dengan
    # `authorId` yang dikirim server.
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
    github_connected: bool = Field(default=False, serialization_alias="githubConnected", validation_alias="githubConnected")
    github_username: Optional[str] = Field(default=None, serialization_alias="githubUsername", validation_alias="githubUsername")
    cv_file_name: Optional[str] = Field(default=None, serialization_alias="cvFileName", validation_alias="cvFileName")
    cv_uploaded_at: Optional[datetime] = Field(default=None, serialization_alias="cvUploadedAt", validation_alias="cvUploadedAt")

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

class CVResponse(BaseModel):
    file_name: str = Field(serialization_alias="fileName", validation_alias="fileName")
    uploaded_at: str = Field(serialization_alias="uploadedAt", validation_alias="uploadedAt")

    model_config = ConfigDict(populate_by_name=True)

class BadgeItem(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    tier: str
    earned: bool = False
    earned_at: Optional[datetime] = Field(default=None, serialization_alias="earnedAt", validation_alias="earnedAt")

    model_config = ConfigDict(populate_by_name=True)
