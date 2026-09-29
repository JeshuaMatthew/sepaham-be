from sqlalchemy import Column, Text, Integer, ForeignKey, DateTime, text as sa_text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from src.app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    emoji = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    tagline = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    description = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    accent = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    match_tags = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))
    tech_stack = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))
    sort_order = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))

class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Text, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    role_title = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    role_emoji = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    role_scores = Column(JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"), onupdate=sa_text("now()"))

    user = relationship("User")
    role = relationship("Role")

class InternshipContact(Base):
    __tablename__ = "internship_contacts"

    id = Column(Text, primary_key=True)
    company = Column(Text, nullable=False)
    emoji = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    position = Column(Text, nullable=False)
    role_id = Column(Text, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    location = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    type = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    pic = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    contact = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    note = Column(Text, nullable=True)

class DevQuote(Base):
    __tablename__ = "dev_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    text = Column(Text, nullable=False)
    author = Column(Text, nullable=False, default="", server_default=sa_text("''"))

class AiInternship(Base):
    __tablename__ = "ai_internships"

    id = Column(Text, primary_key=True)
    company = Column(Text, nullable=False)
    emoji = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    role = Column(Text, nullable=False)
    location = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    type = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    match_percent = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    tags = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))

class LofiTrack(Base):
    __tablename__ = "lofi_tracks"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    artist = Column(Text, nullable=False, default="", server_default=sa_text("''"))

