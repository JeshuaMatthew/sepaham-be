"""align_profiles_role_with_user_preferences

Revision ID: c9d4e17a2b83
Revises: b7e1c93d5a48
Create Date: 2026-09-27 16:20:00.000000

Migrasi `8f2c6d41b7a3` menyelaraskan `user_preferences` ke `profiles`, tapi
menyfalkat arah sebenarnya. Akar masalahnya adalah onboarding hanya menulis
`user_preferences`, sedangkan hampir semua modul lain membaca role dari
`profiles.role_title`:

  - collab    -> `author_role` di kartu request
  - community -> label role di daftar anggota & DM
  - faculty   -> kolom "role" di daftar mahasiswa
  - profile   -> Dev-Card
  - ai        -> konteks AI (hanya jatuh ke `user_preferences` kalau
                 `profiles.role_title` kosong)

Akibatnya user yang BARU menyelesaikan onboarding punya `user_preferences`
terisi tapi `profiles.role_title` kosong: role-nya tidak muncul di kartu
request-nya sendiri, tidak muncul di daftar mahasiswa untuk dosen, dan tidak
muncul di Dev-Card.

Dua perbaikan:

1. `onboarding_service.evaluate_assessment` sekarang menulis
   `profiles.role_title` + `profiles.role_emoji` bersamaan dengan
   `user_preferences`, jadi onboarding tidak lagi bisa menghasilkan drift.
2. Migrasi ini menyamakan 6 akun demo yang masih menyimpan kategori singkat
   ("Frontend") menjadi nama role kanonik dari tabel `roles` ("Frontend
   Engineer") — nilai yang sama dengan yang ditulis endpoint evaluate —
   serta mengisi `profiles.role_emoji` yang tadinya kosong untuk semua akun.

Baris tanpa `user_preferences` (akun dosen) tidak disentuh.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c9d4e17a2b83"
down_revision: Union[str, Sequence[str], None] = "b7e1c93d5a48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nilai `profiles.role_title` lama (kategori singkat) per email, supaya
# downgrade mengembalikan persis data sebelumnya.
PREVIOUS_ROLE_TITLES = {
    "budi@sepaham.local": "Backend",
    "kevin@sepaham.local": "Fullstack",
    "nadia@sepaham.local": "UI/UX",
    "rian@sepaham.local": "Mobile",
    "salsa@sepaham.local": "Data/ML",
    "siti@sepaham.local": "Frontend",
}


def upgrade() -> None:
    op.execute(
        """
        UPDATE profiles p
        SET role_title = r.title,
            role_emoji = r.emoji
        FROM user_preferences up
        JOIN roles r ON r.id = up.role_id
        WHERE p.user_id = up.user_id
        """
    )


def downgrade() -> None:
    for email, previous in PREVIOUS_ROLE_TITLES.items():
        op.execute(
            """
            UPDATE profiles p
            SET role_title = :role_title, role_emoji = ''
            FROM users u
            WHERE p.user_id = u.id AND u.email = :email
            """,
            {"role_title": previous, "email": email},
        )
