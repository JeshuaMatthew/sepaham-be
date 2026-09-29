"""fill_role_accent_and_emoji

Revision ID: b7e1c93d5a48
Revises: f2b8c6d41e90
Create Date: 2026-09-27 15:40:00.000000

10 role pertama (`roles.sort_order` 1-10) punya `accent` dan `emoji` kosong.
Dua akibat yang terlihat:

1. `RoleRecommendationContainer` mewarnai nama role yang direkomendasikan
   dengan `style={{ color: role.accent }}`. Dengan accent kosong, teks itu
   memakai warna body -- aksennya sama sekali tidak terlihat.
2. Emoji ikut terkirim ke `user_preferences.role_emoji` lewat
   `POST /preferences`, jadi kolom itu kosong untuk semua role tersebut.

Migrasi ini mengisi keduanya. Semua accent dipilih dengan kontras >= 4.5:1 di
atas `--theme-canvas` gelap (#1c1c1c) supaya tetap terbaca sebagai teks, dan
saling berbeda agar 17 role mudah dibedakan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e1c93d5a48"
down_revision: Union[str, Sequence[str], None] = "f2b8c6d41e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# role_id -> (accent, emoji)
ROLE_ACCENT_EMOJI = {
    "frontend-engineer": ("#38bdf8", "\U0001f4bb"),  # laptop
    "backend-engineer": ("#a78bfa", "\U0001f9e9"),  # puzzle piece
    "mobile-developer": ("#34d399", "\U0001f4f1"),  # mobile phone
    "ml-engineer": ("#f472b6", "\U0001f916"),  # robot
    "data-analyst": ("#fbbf24", "\U0001f4ca"),  # bar chart
    "devops-engineer": ("#fb923c", "\U0001f433"),  # whale
    "security-engineer": ("#f87171", "\U0001f510"),  # locked key
    "game-developer": ("#c084fc", "\U0001f3ae"),  # video game
    "ui-ux-designer": ("#f9a8d4", "\U0001f3a8"),  # artist palette
    "fullstack-engineer": ("#2dd4bf", "\U0001f9e9"),  # puzzle piece
}


def upgrade() -> None:
    for role_id, (accent, emoji) in ROLE_ACCENT_EMOJI.items():
        op.execute(
            sa.text("UPDATE roles SET accent = :accent, emoji = :emoji WHERE id = :rid").bindparams(
                accent=accent, emoji=emoji, rid=role_id
            )
        )

    # `user_preferences.role_emoji` adalah salinan dari role saat onboarding
    # diselesaikan. Sinkronkan supaya tidak ada baris yang tertinggal kosong.
    op.execute(
        """
        UPDATE user_preferences p
        SET role_emoji = r.emoji
        FROM roles r
        WHERE p.role_id = r.id
          AND COALESCE(p.role_emoji, '') = ''
          AND COALESCE(r.emoji, '') <> ''
        """
    )

    # Semua roadmap masih `emoji` kosong dan `color` = '#e5e5e5' (warna
    # placeholder, sama seperti accent role yang kosong). Roadmap berelasi ke
    # role lewat `role_id`, jadi warna & emoji-nya bisa diwarisi dari role.
    op.execute(
        """
        UPDATE roadmaps rm
        SET color = r.accent, emoji = r.emoji
        FROM roles r
        WHERE rm.role_id = r.id
          AND (COALESCE(rm.color, '') IN ('', '#e5e5e5') OR COALESCE(rm.emoji, '') = '')
        """
    )


def downgrade() -> None:
    # Kembalikan hanya 10 role yang disentuh migrasi ini ke kondisi kosong
    # semula. Role 11-17 tidak diubah, jadi tidak perlu dikembalikan.
    role_ids = ", ".join("'%s'" % r for r in ROLE_ACCENT_EMOJI)
    for role_id in ROLE_ACCENT_EMOJI:
        op.execute(
            sa.text("UPDATE roles SET accent = '', emoji = '' WHERE id = :rid").bindparams(
                rid=role_id
            )
        )

    op.execute(
        "UPDATE user_preferences SET role_emoji = '' WHERE role_id IN (%s)" % role_ids
    )

    op.execute(
        "UPDATE roadmaps SET color = '#e5e5e5', emoji = '' WHERE role_id IN (%s)" % role_ids
    )
