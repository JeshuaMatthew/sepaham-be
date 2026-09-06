from sqlalchemy import Column, Text, Integer, text
from sqlalchemy.orm import relationship
from src.app.core.database import Base
from src.app.core.enums import BadgeTier
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

class Badge(Base):
    __tablename__ = "badges"
    
    id = Column(
        Text,
        primary_key=True,
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
    
    icon = Column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    
    tier = Column(
        PgEnum(
            BadgeTier,
            name="badge_tier",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=BadgeTier.COMMON.value,
        server_default=text("'common'"),
    )
    
    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    
    user_badges = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")
