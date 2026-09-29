"""remove_test_accounts

Revision ID: f2b8c6d41e90
Revises: 5d1a7c3e9b02
Create Date: 2026-09-27 15:10:00.000000

Dua akun sisa pengujian bocor ke database demo:

  - googletest@sepaham.id ("Google Test User") - artefak uji SSO Google,
    tanpa data lain sama sekali (0 profile, 0 badge, 0 pesan).
  - regression.tester@sepaham.local — Akun sekali pakai untuk regresi,
    hanya punya satu `user_preferences` hasil evaluate.

Keduanya tidak mewakili pengguna nyata dan muncul di daftar akun pada panel
dosen, jadi dihapus. Baris anak ikut terhapus lewat ON DELETE CASCADE/SET NULL
sesuai definisi foreign key.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2b8c6d41e90"
down_revision: Union[str, Sequence[str], None] = "5d1a7c3e9b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEST_EMAILS = ("googletest@sepaham.id", "regression.tester@sepaham.local")


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM users WHERE email IN :emails"
        ).bindparams(sa.bindparam("emails", value=list(TEST_EMAILS), expanding=True))
    )


def downgrade() -> None:
    # Akun uji tidak pernah ada di produksi dan tidak menyimpan data
    # bermakna, jadi tidak dikembalikan.
    pass
