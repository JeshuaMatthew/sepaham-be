"""add_weight_to_questions

Revision ID: a1b2c3d4e5f6
Revises: f6c2a41d9e83
Create Date: 2026-09-28 10:00:00.000000

Menambahkan kolom `weight` ke tabel `questions` untuk menentukan bobot
pertanyaan dalam penentuan role. Default 1.0 (semua soal setara).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f6c2a41d9e83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sama seperti `5d1a7c3e9b02`: tabel `questions` belum ada di database
    # kosong (dibuat lengkap oleh `f6a7b8c9d0e1` di ujung rantai).
    if not sa.inspect(op.get_bind()).has_table("questions"):
        return
    op.add_column(
        "questions",
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
    )


def downgrade() -> None:
    op.drop_column("questions", "weight")
