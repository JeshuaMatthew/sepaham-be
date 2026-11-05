"""remove_weighted_scoring_remnants

Revision ID: d2c3e4f5a6b7
Revises: c1a2b3d4e5f6
Create Date: 2026-11-03 16:45:00.000000

Menghapus seluruh kolom sisa mekanisme lama (skor berbobot / scoring / choice)
agar selaras dengan Forward Chaining klasik murni biner (True/False):
- questions.weight
- questions.question_type
- questions.options
- user_preferences.role_scores
- rules.min_confidence_score (jika masih tersisa)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2c3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Hapus kolom sisa pembobotan dan pilihan ganda dari questions
    bind.execute(sa.text("ALTER TABLE questions DROP COLUMN IF EXISTS weight"))
    bind.execute(sa.text("ALTER TABLE questions DROP COLUMN IF EXISTS question_type"))
    bind.execute(sa.text("ALTER TABLE questions DROP COLUMN IF EXISTS options"))

    # 2. Hapus kolom role_scores dari user_preferences
    bind.execute(sa.text("ALTER TABLE user_preferences DROP COLUMN IF EXISTS role_scores"))

    # 3. Pastikan min_confidence_score bersih dari rules
    bind.execute(sa.text("ALTER TABLE rules DROP COLUMN IF EXISTS min_confidence_score"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS weight DOUBLE PRECISION NOT NULL DEFAULT 1.0"))
    bind.execute(sa.text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_type VARCHAR(20) NOT NULL DEFAULT 'binary'"))
    bind.execute(sa.text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS options JSONB"))
    bind.execute(sa.text("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS role_scores JSONB NOT NULL DEFAULT '{}'::jsonb"))
    bind.execute(sa.text("ALTER TABLE rules ADD COLUMN IF NOT EXISTS min_confidence_score DOUBLE PRECISION DEFAULT 0.7"))
