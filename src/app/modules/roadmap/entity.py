from sqlalchemy import (
    Column, Text, Integer, Float, Boolean, ForeignKey, DateTime,
    UniqueConstraint, text as sa_text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, ENUM as PgEnum
from sqlalchemy.orm import relationship

from src.app.core.database import Base
from src.app.core.enums import RoadmapDifficulty

class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Text, primary_key=True)
    role_id = Column(Text, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    title = Column(Text, nullable=False)
    emoji = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    color = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    description = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    difficulty = Column(
        PgEnum(
            RoadmapDifficulty,
            name="roadmap_difficulty",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=RoadmapDifficulty.BEGINNER.value,
        server_default=sa_text("'Beginner'"),
    )
    match_tags = Column(ARRAY(Text), nullable=False, default=list, server_default=sa_text("'{}'"))
    author = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    style = Column(JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"), onupdate=sa_text("now()"))

    nodes = relationship("RoadmapNode", back_populates="roadmap", cascade="all, delete-orphan")
    edges = relationship("RoadmapEdge", back_populates="roadmap", cascade="all, delete-orphan")

class RoadmapNode(Base):
    __tablename__ = "roadmap_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    roadmap_id = Column(Text, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False)
    node_key = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    emoji = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    x = Column(Float, nullable=False, default=0.0, server_default=sa_text("0"))
    y = Column(Float, nullable=False, default=0.0, server_default=sa_text("0"))
    group_name = Column(Text, nullable=True)
    image = Column(Text, nullable=True)
    title_inside = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    always_unlocked = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    optional = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    article = Column(Text, nullable=True)
    submission = Column(JSONB, nullable=True)
    resources = Column(JSONB, nullable=True)
    missions = Column(JSONB, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))

    roadmap = relationship("Roadmap", back_populates="nodes")

    __table_args__ = (
        UniqueConstraint("roadmap_id", "node_key", name="uq_roadmap_node"),
    )

class RoadmapEdge(Base):
    __tablename__ = "roadmap_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    roadmap_id = Column(Text, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False)
    edge_key = Column(Text, nullable=False)
    source_key = Column(Text, nullable=False)
    target_key = Column(Text, nullable=False)
    dashed = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    optional = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    animated = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))

    roadmap = relationship("Roadmap", back_populates="edges")

    __table_args__ = (
        UniqueConstraint("roadmap_id", "edge_key", name="uq_roadmap_edge"),
    )

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    roadmap_id = Column(Text, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False)
    node_key = Column(Text, nullable=False)
    done = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    file_name = Column(Text, nullable=True)
    text_answer = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    quiz_answers = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"), onupdate=sa_text("now()"))

    user = relationship("User")
    roadmap = relationship("Roadmap")

    __table_args__ = (
        UniqueConstraint("user_id", "roadmap_id", "node_key", name="uq_user_roadmap_submission"),
    )

class RoadmapActivity(Base):
    __tablename__ = "roadmap_activity"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    roadmap_id = Column(Text, ForeignKey("roadmaps.id", ondelete="CASCADE"), primary_key=True)
    last_active_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"))

    user = relationship("User")
    roadmap = relationship("Roadmap")
