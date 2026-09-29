import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.app.core.database import Base


class Pillar(Base):
    __tablename__ = "pillars"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    questions = relationship("Question", back_populates="pillar")


class Fact(Base):
    __tablename__ = "facts"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)

    questions = relationship("Question", back_populates="fact")


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pillar_id = Column(String, ForeignKey("pillars.id"), nullable=True)
    fact_id = Column(String, ForeignKey("facts.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)
    options = Column(JSONB, nullable=True)
    # Bobot pertanyaan untuk penentuan role. Default 1.0 (semua soal setara).
    weight = Column(Float, nullable=False, default=1.0, server_default="1.0")
    # Urutan tampil per pillar. Kolom ini wajib karena `id` berupa UUID —
    # tanpa sort_order urutan pertanyaan yang dilihat mahasiswa acak.
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")

    pillar = relationship("Pillar", back_populates="questions")
    fact = relationship("Fact", back_populates="questions")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(String, ForeignKey("roles.id"), nullable=True)
    conditions = Column(JSONB, nullable=False)
    min_confidence_score = Column(Float, nullable=True)


class UserOnboardingSession(Base):
    __tablename__ = "user_onboarding_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    essay_text = Column(Text, nullable=True)
    selected_pillars = Column(JSONB, nullable=True)
    collected_facts = Column(JSONB, nullable=True)
    recommended_role_id = Column(String, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
