from sqlalchemy import (
    Column, Text, Integer, Boolean, ForeignKey, DateTime, text as sa_text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM as PgEnum
from sqlalchemy.orm import relationship

from src.app.core.database import Base
from src.app.core.enums import CollabStatus, ApplicantStatus

class CollabRequest(Base):
    __tablename__ = "collab_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name = Column(Text, nullable=False)
    author_avatar = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    author_role = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    needed_roles = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))
    tech_stack = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))
    tags = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))
    repo_url = Column(Text, nullable=True)
    community_id = Column(Text, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    members_current = Column(Integer, nullable=False, default=1, server_default=sa_text("1"))
    members_needed = Column(Integer, nullable=False, default=2, server_default=sa_text("2"))
    status = Column(
        PgEnum(
            CollabStatus,
            name="collab_status",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=CollabStatus.OPEN.value,
        server_default=sa_text("'open'"),
    )
    closed = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"), onupdate=sa_text("now()"))

    images = relationship("CollabRequestImage", back_populates="request", cascade="all, delete-orphan")
    applicants = relationship("CollabApplicant", back_populates="request", cascade="all, delete-orphan")
    server = relationship("Server")

class CollabRequestImage(Base):
    __tablename__ = "collab_request_images"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    request_id = Column(UUID(as_uuid=True), ForeignKey("collab_requests.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))

    request = relationship("CollabRequest", back_populates="images")

class CollabApplicant(Base):
    __tablename__ = "collab_applicants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    request_id = Column(UUID(as_uuid=True), ForeignKey("collab_requests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(Text, nullable=False)
    avatar = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    role = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    message = Column(Text, nullable=True)
    status = Column(
        PgEnum(
            ApplicantStatus,
            name="applicant_status",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ApplicantStatus.PENDING.value,
        server_default=sa_text("'pending'"),
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    request = relationship("CollabRequest", back_populates="applicants")
    user = relationship("User")
