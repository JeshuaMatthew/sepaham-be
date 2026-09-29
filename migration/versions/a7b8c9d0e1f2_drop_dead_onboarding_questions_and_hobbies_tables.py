"""drop_dead_onboarding_questions_and_hobbies_tables

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-29 13:00:00.000000

Menghapus tabel `onboarding_questions` dan `hobbies`.

Kedua tabel di-seed tapi tidak dibaca atau ditulis endpoint mana pun:
soal onboarding yang dipakai mahasiswa ada di tabel `questions` (dengan
pillar_id/fact_id/question_type), dan tidak ada fitur hobi di aplikasi.
Mempertahankannya hanya menambah permukaan yang menyesatkan — seolah ada
data yang dipakai padahal tidak.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS onboarding_questions"))
    bind.execute(sa.text("DROP TABLE IF EXISTS hobbies"))


def downgrade() -> None:
    # Tidak dipulihkan: tabel-tabel ini tidak pernah dipakai, jadi tidak ada
    # skema yang perlu dikembalikan.
    pass
