"""derive_user_preference_titles_from_roles_title

Revision ID: d4e8a35b1c76
Revises: c9d4e17a2b83
Create Date: 2026-09-27 17:05:00.000000

Tiga baris `user_preferences` masih menyimpan `role_title` dari `roles.name`:

    budi  -> user_preferences "Backend Developer"
          -> profiles          "Backend Engineer"
          -> yang ditulis app  "Backend Engineer"  (role_obj.title)

`roles.name` tidak pernah dipakai backend maupun frontend untuk ditampilkan;
`roles.title` yang dipakai. Dan `evaluate_assessment` menulis `role_obj.title`.
Jadi data lama ini bukan cuma berbeda dengan `profiles`, tapi juga berbeda dengan
nilai yang akan ditulis aplikasi di onboarding berikutnya — artinya setiap pengguna
yang onboarding ulang akan melihat role-nya berubah di satu layar saja.

Migrasi ini menjadikan `roles.title` satu-satunya sumber teks role, supaya:

  - `user_preferences.role_title` == `profiles.role_title` == yang ditulis app
  - Home/Roadmap "Untukmu", Dev-Card, kartu collab, dan daftar mahasiswa untuk
    dosen berhenti menampilkan dua nama berbeda untuk orang yang sama

Baris tanpa `role_id` (atau `role_id` yang tidak ada di `roles`) tidak
disentuh, karena tidak ada sumber teks yang bisa dipercaya untuk baris itu.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8a35b1c76"
down_revision: Union[str, Sequence[str], None] = "c9d4e17a2b83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE user_preferences up
        SET role_title = r.title,
            role_emoji = r.emoji,
            updated_at = now()
        FROM roles r
        WHERE r.id = up.role_id
          AND (up.role_title IS DISTINCT FROM r.title
               OR up.role_emoji IS DISTINCT FROM r.emoji)
        """
    )


def downgrade() -> None:
    # Kembalikan konvensi lama: teks role diambil dari `roles.name`.
    op.execute(
        """
        UPDATE user_preferences up
        SET role_title = r.name,
            updated_at = now()
        FROM roles r
        WHERE r.id = up.role_id
        """
    )
