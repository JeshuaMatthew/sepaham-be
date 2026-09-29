"""add_question_sort_order

Revision ID: 5d1a7c3e9b02
Revises: 8f2c6d41b7a3
Create Date: 2026-09-27 14:20:00.000000

`questions` tidak punya kolom urutan, sehingga `GET /v1/onboarding/questions?pillar=`
mengurutkan dengan `ORDER BY id`. Karena `id` adalah UUID, urutan pertanyaan yang
diter студen acak dan tidak bisa diatur oleh dosen — contohnya pillar `data_ai`
terkirim dengan urutan choice, scale, binary, scale, scale, binary.

Migrasi ini menambah `questions.sort_order`, meng-backfill-nya dengan urutan
saat ini per pillar (agar urutan yang sudah tampil tidak berubah), lalu
mengeindeks `(pillar_id, sort_order)`.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5d1a7c3e9b02"
down_revision: Union[str, Sequence[str], None] = "8f2c6d41b7a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabel `questions` belum ada di database kosong — ia dibuat lengkap
    # (termasuk `sort_order`) oleh `f6a7b8c9d0e1` di ujung rantai. Kalau tabel
    # belum ada, lewati saja.
    if not sa.inspect(op.get_bind()).has_table("questions"):
        return
    op.add_column(
        "questions",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    # Backfill: tetapkan urutan berurutan per pillar, mengikuti urutan lama
    # (ORDER BY id) supaya urutan yang sudah pernah dilihat mahasiswa tetap sama.
    op.execute(
        """
        UPDATE questions q
        SET sort_order = ranked.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY pillar_id ORDER BY id) - 1 AS rn
            FROM questions
        ) ranked
        WHERE q.id = ranked.id
        """
    )
    op.create_index(
        "ix_questions_pillar_sort",
        "questions",
        ["pillar_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_questions_pillar_sort", table_name="questions")
    op.drop_column("questions", "sort_order")
