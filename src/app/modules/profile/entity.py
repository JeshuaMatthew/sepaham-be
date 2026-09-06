from sqlalchemy import Column, text, Text, DateTime, ForeignKey, VARCHAR, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.app.core.database import Base

class Profile(Base):
    __tablename__ = "profiles"
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True, 
        nullable=False,
    )
    
    avatar_url = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    username = Column(
        Text,
        nullable=True,
        unique=True,
    )
    
    university = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    batch = Column(
        Integer,
        nullable=True,
    )
    
    role_title = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    role_emoji = Column(
        Text,
        default="",
        server_default=text("''"),
        nullable=False,
    )
    
    bio = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    location = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    github_connected = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    
    github_username = Column(
        Text,
        nullable=True,
    )
    
    cv_file_name = Column(
        Text,
        nullable=True,
    )
    
    cv_uploaded_at = Column(
        DateTime(timezone=True), 
        nullable=True,
    )
    
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    user = relationship("User", back_populates="profile")