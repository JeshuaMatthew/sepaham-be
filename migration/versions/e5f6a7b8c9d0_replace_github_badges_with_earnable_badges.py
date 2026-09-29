"""replace_github_badges_with_earnable_badges

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-29 12:00:00.000000

Mengganti katalog badge dengan badge yang syaratnya bisa diukur dari aksi di
aplikasi ini.

Katalog lama (first-commit, streak-7, streak-30, polyglot, contributor,
rising-star, night-owl, mentor) syaratnya memakai data GitHub — jumlah commit,
streak harian, bahasa, bintang, PR — yang tidak tersedia lewat API publik
GitHub tanpa token OAuth. Tidak ada kode yang pernah memberi badge itu
(`UserBadge(` tidak pernah di-instantiate di `src/`); 13 baris `user_badges`
semuanya dari seed. Badge yang tidak akan pernah bisa didapat adalah data
dummy juga.

Katalog baru semuanya terukur dari database aplikasi sendiri:

- langkah-pertama : 1 submission roadmap selesai
- konsisten       : 5 submission selesai
- penjelajah      : 10 submission selesai
- kolaborator     : 1 request Cari Tim dibuat
- komunikator     : 10 pesan community terkirim
- profil-lengkap  : CV diunggah

`user_badges` lama ikut terhapus lewat FK `ON DELETE CASCADE`, karena badge
id-nya tidak ada lagi. Itu memang tujuannya: kepemilikan lama semuanya dari
seed, bukan dari aksi nyata.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_BADGES = [
    ("langkah-pertama", "Langkah Pertama", "Menyelesaikan 1 skill roadmap.", "common", 1),
    ("konsisten", "Konsisten", "Menyelesaikan 5 skill roadmap.", "rare", 2),
    ("penjelajah", "Penjelajah", "Menyelesaikan 10 skill roadmap.", "epic", 3),
    ("kolaborator", "Kolaborator", "Membuat 1 request Cari Tim.", "common", 4),
    ("komunikator", "Komunikator", "Mengirim 10 pesan di community.", "rare", 5),
    ("profil-lengkap", "Profil Lengkap", "Mengunggah CV.", "common", 6),
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM badges"))
    for badge_id, name, description, tier, sort_order in NEW_BADGES:
        bind.execute(
            sa.text(
                """
                INSERT INTO badges (id, name, description, icon, tier, sort_order)
                VALUES (:id, :name, :description, '', :tier, :sort_order)
                """
            ),
            {
                "id": badge_id,
                "name": name,
                "description": description,
                "tier": tier,
                "sort_order": sort_order,
            },
        )


def downgrade() -> None:
    # Katalog lama tidak dipulihkan: isinya tidak pernah bisa didapat lewat
    # aksi nyata, jadi memulihkannya berarti memulihkan data dummy.
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM badges"))
