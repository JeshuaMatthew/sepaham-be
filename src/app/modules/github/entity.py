from sqlalchemy import Column, Text, Integer, ForeignKey, DateTime, text as sa_text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.app.core.database import Base

class GithubStats(Base):
    __tablename__ = "github_stats"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    username = Column(Text, nullable=False)
    # Kolom berikut nullable: API publik GitHub tidak menyediakan jumlah commit,
    # streak harian, maupun grafik kontribusi tanpa token OAuth. `NULL` berarti
    # "tidak diketahui". Kolom ini pernah NOT NULL dengan default 0, yang
    # membuat frontend menampilkan "0 commit" untuk data yang sebenarnya tidak
    # pernah diambil.
    total_commits = Column(Integer, nullable=True, default=None)
    current_streak = Column(Integer, nullable=True, default=None)
    longest_streak = Column(Integer, nullable=True, default=None)
    public_repos = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    top_languages = Column(JSONB, nullable=False, default=list, server_default=sa_text("'[]'::jsonb"))
    weeks = Column(JSONB, nullable=True, default=None)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()"), onupdate=sa_text("now()"))

    user = relationship("User")

class GithubRepo(Base):
    __tablename__ = "github_repos"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    stars = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    forks = Column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    language = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    language_color = Column(Text, nullable=False, default="", server_default=sa_text("''"))
    url = Column(Text, nullable=False, default="", server_default=sa_text("''"))

    user = relationship("User")
