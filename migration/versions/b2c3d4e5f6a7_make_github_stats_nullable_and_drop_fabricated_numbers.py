"""make_github_stats_nullable_and_drop_fabricated_numbers

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-29 09:30:00.000000

Mengubah `github_stats.total_commits`, `current_streak`, `longest_streak`, dan
`weeks` menjadi nullable, lalu mengosongkan nilainya.

Alasannya: API publik GitHub tidak menyediakan angka-angka itu tanpa token
OAuth. Sebelumnya `github/service.py` mengarangnya: `total_commits =
repos * 15`, `current_streak` dan `longest_streak` konstanta, `weeks` dari
konstanta `DEMO_WEEKS`. Kolom `NOT NULL DEFAULT 0` ikut memaksa angka itu
tampil sebagai "0 commit", yang berbeda maknanya dari "tidak diketahui".

Migrasi ini sekaligus membuang angka yang sudah tersimpan, karena nilainya
memang tidak pernah diukur.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "github_stats",
        "total_commits",
        existing_type=sa.Integer(),
        nullable=True,
        existing_server_default="0",
        server_default=None,
    )
    op.alter_column(
        "github_stats",
        "current_streak",
        existing_type=sa.Integer(),
        nullable=True,
        existing_server_default="0",
        server_default=None,
    )
    op.alter_column(
        "github_stats",
        "longest_streak",
        existing_type=sa.Integer(),
        nullable=True,
        existing_server_default="0",
        server_default=None,
    )
    op.alter_column(
        "github_stats",
        "weeks",
        existing_type=postgresql.JSONB(),
        nullable=True,
        existing_server_default=sa.text("'[]'::jsonb"),
        server_default=None,
    )

    # Buang angka yang tidak pernah diukur. `public_repos` dan `top_languages`
    # tetap dipertahankan karena itu benar-benar berasal dari GitHub.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE github_stats
               SET total_commits  = NULL,
                   current_streak = NULL,
                   longest_streak = NULL,
                   weeks          = NULL
            """
        )
    )


def downgrade() -> None:
    # Isi ulang dengan 0 supaya kolom bisa dibuat NOT NULL kembali. Angka ini
    # tidak bermakna sebagai data, tapi tidak ada cara memulihkan nilai yang
    # aslinya tidak pernah ada.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE github_stats
               SET total_commits  = COALESCE(total_commits, 0),
                   current_streak = COALESCE(current_streak, 0),
                   longest_streak = COALESCE(longest_streak, 0),
                   weeks          = COALESCE(weeks, '[]'::jsonb)
            """
        )
    )

    op.alter_column(
        "github_stats",
        "total_commits",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "github_stats",
        "current_streak",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "github_stats",
        "longest_streak",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "github_stats",
        "weeks",
        existing_type=postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )

