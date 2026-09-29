"""make_role_accents_pass_contrast_in_both_themes

Revision ID: f6c2a41d9e83
Revises: d4e8a35b1c76
Create Date: 2026-09-27 17:40:00.000000

`roles.accent` di-render sebagai warna teks pada heading hasil asesmen
(`ResultRevealStep`, `text-2xl font-bold` = 24px bold) dan sebagai warna
dekoratif (bar kecocokan, border kartu, chip server, bar bahasa).

Dua masalah:

1. Sebagian accent gagal kontras di kanvas terang. Di permukaan terang,
   12 dari 17 accent bahkan gagal 4.5:1.

2. Mengangkat semuanya ke 4.5:1 secara MATEMATIS TIDAK MUNGKIN untuk satu hex
   yang dipakai di kedua tema. Permukaan teks sebenarnya adalah
   `--theme-surface`:

     dark  : rgba(255,255,255,0.045) atas #1c1c1c  -> L ~ 0.0196
     light : #ffffff                                   -> L = 1.0

   Agar satu warna punya kontras >= 4.5:1 terhadap KEDUANYA, luminansinya
   harus >= 0.227 (untuk gelap) sekaligus <= 0.113 (untuk terang) — rentang
   yang kosong.

Ambang yang dipakai karenanya 3:1, dan ini bukan pelonggaran asal-asalan:

  - WCAG 1.4.3: teks LARGE (>= 18.66px bold atau >= 24px regular) cukup 3:1.
    Heading ini 24px bold -> large text.
  - WCAG 1.4.11: elemen dekoratif/non-teks cukup 3:1, dan bar kecocokan
    memang redundan dengan angka persen yang berdiri di sampingnya.

Dengan 3:1, 5 accent sudah lolos di kedua tema dan dibiarkan apa adanya.
12 sisanya digeser lightness-nya dengan hue & saturation yang sama, sedekat
mungkin dengan warna aslinya, supaya identitas warna role tidak hilang.

`roadmaps.color` ikut disinkronkan karena selama ini ia menyalin
`roles.accent`; kalau tidak, perbaikan di sini membuat dua sumber warna yang
berbeda untuk role yang sama.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6c2a41d9e83"
down_revision: Union[str, Sequence[str], None] = "d4e8a35b1c76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# role_id -> (accent lama, accent baru). Hanya 12 yang gagal 3:1 di salah satu
# tema; 5 lainnya sudah lolos dan tidak disentuh.
ACCENT_FIXES = {
    "frontend-engineer": ("#38bdf8", "#089EE0"),
    "backend-engineer": ("#a78bfa", "#9F80FA"),
    "mobile-developer": ("#34d399", "#24A878"),
    "ml-engineer": ("#f472b6", "#F25EAC"),
    "data-analyst": ("#fbbf24", "#BE8A03"),
    "devops-engineer": ("#fb923c", "#F06F05"),
    "security-engineer": ("#f87171", "#F76363"),
    "game-developer": ("#c084fc", "#B874FC"),
    "ui-ux-designer": ("#f9a8d4", "#F45AAE"),
    "fullstack-engineer": ("#2dd4bf", "#22A595"),
    "data-engineer": ("#10B981", "#0FA976"),
    "ux-researcher": ("#F59E0B", "#CE8408"),
    "scrum-master": ("#14B8A6", "#12A695"),
}


def _set_accent(bind, role_id: str, accent: str) -> None:
    """`op.execute()` di Alembic 1.19 tidak menerima bind params, jadi pakai
    bind langsung dengan API SQLAlchemy yang benar."""
    bind.execute(
        sa.text("UPDATE roles SET accent = :accent WHERE id = :role_id"),
        {"accent": accent, "role_id": role_id},
    )


def upgrade() -> None:
    bind = op.get_bind()
    for role_id, (_, new_accent) in ACCENT_FIXES.items():
        _set_accent(bind, role_id, new_accent)

    # `roadmaps.color` selama ini berisi salinan `roles.accent`; ikuti agar
    # keduanya tidak berbeda untuk role yang sama.
    bind.execute(
        sa.text(
            """
            UPDATE roadmaps r
            SET color = ro.accent
            FROM roles ro
            WHERE ro.id = r.role_id
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    for role_id, (old_accent, _) in ACCENT_FIXES.items():
        _set_accent(bind, role_id, old_accent)

    # Balikkan juga `roadmaps.color` ke salinan lama.
    bind.execute(
        sa.text(
            """
            UPDATE roadmaps r
            SET color = ro.accent
            FROM roles ro
            WHERE ro.id = r.role_id
            """
        )
    )
