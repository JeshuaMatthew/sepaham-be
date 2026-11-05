from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field

class RoleItem(BaseModel):
    id: str
    title: str
    emoji: str = ""
    tagline: str = ""
    description: str = ""
    accent: str = ""
    match_tags: list[str] = Field(default_factory=list, serialization_alias="matchTags", validation_alias="matchTags")
    tech_stack: list[str] = Field(default_factory=list, serialization_alias="techStack", validation_alias="techStack")

    model_config = ConfigDict(populate_by_name=True)

class RolesResponse(BaseModel):
    roles: list[RoleItem]

class UserPreferenceResponse(BaseModel):
    role_id: Optional[str] = Field(default=None, serialization_alias="roleId", validation_alias="roleId")
    role_title: str = Field(default="", serialization_alias="roleTitle", validation_alias="roleTitle")
    role_emoji: str = Field(default="", serialization_alias="roleEmoji", validation_alias="roleEmoji")
    role_scores: dict[str, Any] = Field(default_factory=dict, serialization_alias="roleScores", validation_alias="roleScores")

    model_config = ConfigDict(populate_by_name=True)

class UserPreferenceUpdateRequest(BaseModel):
    role_id: Optional[str] = Field(default=None, alias="roleId")
    role_title: str = Field(default="", alias="roleTitle")
    role_emoji: str = Field(default="", alias="roleEmoji")
    role_scores: dict[str, Any] = Field(default_factory=dict, alias="roleScores")

    model_config = ConfigDict(populate_by_name=True)
