from sqlalchemy import Column, Text, ForeignKey, PrimaryKeyConstraint, Boolean, DateTime, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.app.core.database import Base

class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    badge_id = Column(
        Text, 
        ForeignKey("badges.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    earned = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    
    earned_at = Column(
        DateTime(timezone=True), 
        nullable=False,
        server_default=text("now()"),
    )
    
    user = relationship("User", back_populates="user_badges")
    badge = relationship("Badge", back_populates="user_badges")
    
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'badge_id', name='pk_user_badges'),
    )


    