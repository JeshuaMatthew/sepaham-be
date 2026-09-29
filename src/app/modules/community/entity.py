from sqlalchemy import (
    Column, Text, Integer, Boolean, ForeignKey, DateTime,
    PrimaryKeyConstraint, UniqueConstraint, CheckConstraint, text as sa_text
)
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship

from src.app.core.database import Base
from src.app.core.enums import ChannelKind

class Server(Base):
    __tablename__ = "servers"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    initial = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    color = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_team_community = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    banned = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    banned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    banned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    channels = relationship("Channel", back_populates="server", cascade="all, delete-orphan")
    members = relationship("ServerMember", back_populates="server", cascade="all, delete-orphan")

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Text, primary_key=True)
    server_id = Column(Text, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    topic = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    kind = Column(
        PgEnum(
            ChannelKind,
            name="channel_kind",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ChannelKind.TEXT.value,
        server_default=sa_text("'text'"),
    )
    sort_order = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    server = relationship("Server", back_populates="channels")

class ServerMember(Base):
    __tablename__ = "server_members"

    server_id = Column(Text, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    server = relationship("Server", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        PrimaryKeyConstraint("server_id", "user_id", name="pk_server_members"),
    )

class CommunityInvite(Base):
    __tablename__ = "community_invites"

    token = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    server_id = Column(Text, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    server = relationship("Server")

class DirectConversation(Base):
    __tablename__ = "direct_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    user_low = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_high = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    __table_args__ = (
        UniqueConstraint("user_low", "user_high", name="uq_direct_conv_pair"),
        CheckConstraint("user_low < user_high", name="ck_direct_conv_user_order"),
    )

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    channel_id = Column(Text, ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    dm_id = Column(UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name = Column(Text, nullable=False)
    author_avatar = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    body = Column(Text, nullable=True)
    code_language = Column(Text, nullable=True)
    code_content = Column(Text, nullable=True)
    attachment_name = Column(Text, nullable=True)
    attachment_kind = Column(Text, nullable=True)
    attachment_size = Column(Text, nullable=True)
    attachment_url = Column(Text, nullable=True)
    anonymous = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    channel = relationship("Channel")
    dm = relationship("DirectConversation")
    replies = relationship("Message", backref="parent", remote_side=[id])

    __table_args__ = (
        CheckConstraint("channel_id IS NOT NULL OR dm_id IS NOT NULL", name="ck_message_destination"),
    )
