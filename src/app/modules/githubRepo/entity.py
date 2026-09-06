from sqlalchemy import Column, text, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.app.core.database import Base

class GithubRepo(Base):
    __tablename__ = "github_repos"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
    )
    
    name = Column(
        Text,
        nullable=False,
    )
    
    description = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    stars = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    
    forks = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    
    language = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    language_color = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    url = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )

    user = relationship("User", backref="github_repos")

