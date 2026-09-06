from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ServerObj(BaseModel):
    id: str
    name: str
    initial: str = ""
    color: str = ""

class ChannelObj(BaseModel):
    id: str
    server_id: str = Field(serialization_alias="serverId", validation_alias="serverId")
    name: str
    topic: str = ""
    kind: str = "text"

    model_config = ConfigDict(populate_by_name=True)

class CommunityMineItem(BaseModel):
    server: ServerObj
    channels: list[ChannelObj] = Field(default_factory=list)

class CommunityMineResponse(BaseModel):
    communities: list[CommunityMineItem]

class JoinServerResponse(BaseModel):
    server: ServerObj
    channels: list[ChannelObj] = Field(default_factory=list)

class CreateInviteResponse(BaseModel):
    token: str
    server_id: str = Field(serialization_alias="serverId", validation_alias="serverId")

    model_config = ConfigDict(populate_by_name=True)

class MessageAttachment(BaseModel):
    name: str
    kind: str
    size: str

class MessageCode(BaseModel):
    language: str
    content: str

class MessageResponse(BaseModel):
    id: str
    author_id: str = Field(serialization_alias="authorId", validation_alias="authorId")
    author_name: str = Field(serialization_alias="authorName", validation_alias="authorName")
    author_avatar: str = Field(default="", serialization_alias="authorAvatar", validation_alias="authorAvatar")
    timestamp: str = ""
    text: Optional[str] = None
    code: Optional[MessageCode] = None
    attachment: Optional[MessageAttachment] = None
    anonymous: bool = False
    replies: list["MessageResponse"] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class PostMessageRequest(BaseModel):
    text: Optional[str] = None
    code: Optional[MessageCode] = None
    attachment: Optional[MessageAttachment] = None
    parent_id: Optional[str] = Field(default=None, alias="parentId")
    anonymous: bool = False

    model_config = ConfigDict(populate_by_name=True)

class DMItem(BaseModel):
    id: str
    user_id: str = Field(serialization_alias="userId", validation_alias="userId")
    user_name: str = Field(serialization_alias="userName", validation_alias="userName")
    avatar: str = ""
    role: str = ""
    online: bool = True
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class DMsResponse(BaseModel):
    dms: list[DMItem]

class CreateDMRequest(BaseModel):
    user_id: str = Field(alias="userId")

    model_config = ConfigDict(populate_by_name=True)
