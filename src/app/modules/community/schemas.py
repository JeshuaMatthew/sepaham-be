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

class DiscoverServerItem(BaseModel):
    """Server yang bisa ditemukan (belum tentu anggota)."""
    server: ServerObj
    channels: list[ChannelObj] = Field(default_factory=list)
    member_count: int = Field(
        default=0, serialization_alias="memberCount", validation_alias="memberCount"
    )
    joined: bool = False

    model_config = ConfigDict(populate_by_name=True)

class DiscoverServersResponse(BaseModel):
    servers: list[DiscoverServerItem] = Field(default_factory=list)

class CreateInviteResponse(BaseModel):
    token: str
    server_id: str = Field(serialization_alias="serverId", validation_alias="serverId")

    model_config = ConfigDict(populate_by_name=True)

class MessageAttachment(BaseModel):
    name: str
    kind: str
    size: str
    # URL berkas yang sudah diunggah lewat POST /api/chat/attachments.
    # Opsional supaya pesan lama tetap valid, tapi pesan baru wajib ada URL —
    # kalau tidak, lampiran hanya klaim nama tanpa berkas yang bisa dibuka.
    url: Optional[str] = None

class MessageCode(BaseModel):
    language: str
    content: str

class ChatAttachmentResponse(BaseModel):
    name: str
    kind: str
    size: str
    url: str

    model_config = ConfigDict(populate_by_name=True)

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
    # `online` dihapus. Tidak ada presence tracking di aplikasi ini, tapi field
    # ini selalu `True` dan UI memakainya untuk menampilkan titik hijau —
    # artinya setiap user terlihat online terus. Lebih jujur tidak ada titik
    # daripada titik yang selalu menyala.
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class DMsResponse(BaseModel):
    dms: list[DMItem]

class CreateDMRequest(BaseModel):
    user_id: str = Field(alias="userId")

    model_config = ConfigDict(populate_by_name=True)
