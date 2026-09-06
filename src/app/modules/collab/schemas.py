from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class AuthorObj(BaseModel):
    name: str
    avatar: str = ""
    role: str = ""

class CollabRequestItem(BaseModel):
    id: str
    title: str
    description: str = ""
    needed_roles: list[str] = Field(default_factory=list, serialization_alias="neededRoles", validation_alias="neededRoles")
    tech_stack: list[str] = Field(default_factory=list, serialization_alias="techStack", validation_alias="techStack")
    tags: list[str] = Field(default_factory=list)
    repo_url: Optional[str] = Field(default=None, serialization_alias="repoUrl", validation_alias="repoUrl")
    images: list[str] = Field(default_factory=list)
    community_id: Optional[str] = Field(default=None, serialization_alias="communityId", validation_alias="communityId")
    community_name: Optional[str] = Field(default=None, serialization_alias="communityName", validation_alias="communityName")
    author: AuthorObj
    members_current: int = Field(default=1, serialization_alias="membersCurrent", validation_alias="membersCurrent")
    members_needed: int = Field(default=2, serialization_alias="membersNeeded", validation_alias="membersNeeded")
    interested: int = 0
    status: str = "open"
    posted_minutes_ago: int = Field(default=0, serialization_alias="postedMinutesAgo", validation_alias="postedMinutesAgo")

    model_config = ConfigDict(populate_by_name=True)

class CollabRequestsResponse(BaseModel):
    requests: list[CollabRequestItem]

class CreateCollabRequest(BaseModel):
    title: str
    description: str = ""
    needed_roles: list[str] = Field(default_factory=list, alias="neededRoles")
    tech_stack: list[str] = Field(default_factory=list, alias="techStack")
    tags: list[str] = Field(default_factory=list)
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    members_needed: int = Field(default=2, alias="membersNeeded")
    images: list[str] = Field(default_factory=list)
    community_id: Optional[str] = Field(default=None, alias="communityId")
    new_community_name: Optional[str] = Field(default=None, alias="newCommunityName")

    model_config = ConfigDict(populate_by_name=True)

class ApplicantItem(BaseModel):
    id: str
    name: str
    avatar: str = ""
    role: str = ""
    message: Optional[str] = None
    status: str = "pending"
    applied_minutes_ago: int = Field(default=0, serialization_alias="appliedMinutesAgo", validation_alias="appliedMinutesAgo")

    model_config = ConfigDict(populate_by_name=True)

class MyTeamItem(BaseModel):
    request: CollabRequestItem
    applicants: list[ApplicantItem] = Field(default_factory=list)
    community_server_id: Optional[str] = Field(default=None, serialization_alias="communityServerId", validation_alias="communityServerId")

    model_config = ConfigDict(populate_by_name=True)

class MyTeamsResponse(BaseModel):
    teams: list[MyTeamItem]

class ApplyCollabRequest(BaseModel):
    message: Optional[str] = None

class UpdateApplicantStatusRequest(BaseModel):
    status: str
