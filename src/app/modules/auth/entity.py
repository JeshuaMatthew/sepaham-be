from sqlalchemy import Column, text, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.app.core.database import Base
from src.app.core.enums import UserRole
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default= text("gen_random_uuid()")
    )

    email = Column(
        type_= Text,
        unique=True,
        nullable=False,
    )

    password_hash = Column(
        type_=Text,
        nullable=False,
    )

    role = Column(
        "role",
        PgEnum(
            UserRole,
            name="user_role",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=UserRole.STUDENT.value,
        server_default=text("'student'"),
    )

    name = Column(
        type_=Text,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True), 
        nullable=False,
        server_default = text("now()")
        
    )

    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False,
        server_default = text("now()")
    )

    profile = relationship("Profile", back_populates="user", uselist=False)
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")

    