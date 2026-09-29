"""align_user_preferences_with_profile_role

Revision ID: 8f2c6d41b7a3
Revises: c41b7e2a9d10
Create Date: 2026-09-27 13:05:00.000000

`user_preferences` (hasil onboarding) tidak konsisten dengan `profiles.role_title`:

  - Siti Rahma   -> profil "Frontend",  preference "Data Analyst" (data-analyst)
  - Nadia Putri  -> profil "UI/UX",     preference "frontend-engineer"
  - Kevin Wijaya -> profil "Fullstack", preference "frontend-engineer"

Akibatnya tiga layar menampilkan role yang berbeda untuk orang yang sama:
Dev-Card (dari profiles), Home/Roadmap "Untukmu" (dari user_preferences), dan
Career ranking (dari user_preferences.role_scores).

Migrasi ini menyelaraskan `user_preferences` akun demo dengan role profilnya,
lalu menormalkan bentuk `role_scores` menjadi peta seluruh role (0..100) —
bentuk yang sama dengan yang ditulis endpoint `/onboarding/evaluate`, supaya
Career/Roadmap tidak bergantung pada satu kunci saja.
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8f2c6d41b7a3"
down_revision: Union[str, Sequence[str], None] = "c41b7e2a9d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# email -> (role_id yang benar, role kedua sebagai skor pendukung)
DEMO_ROLE_FIXES = {
    "siti@sepaham.local": ("frontend-engineer", "fullstack-engineer"),
    "budi@sepaham.local": ("backend-engineer", "devops-engineer"),
    "nadia@sepaham.local": ("ui-ux-designer", "product-designer"),
    "rian@sepaham.local": ("mobile-developer", "frontend-engineer"),
    "salsa@sepaham.local": ("ml-engineer", "data-analyst"),
    "kevin@sepaham.local": ("fullstack-engineer", "backend-engineer"),
}

PRIMARY_SCORE = 100.0
SECONDARY_SCORE = 60.0


def _build_scores(all_roles: list[str], primary: str, secondary: str) -> dict[str, float]:
    """Peta seluruh role: 0, kecuali role utama (100) dan kedua (60)."""
    scores = {rid: 0.0 for rid in all_roles}
    scores[primary] = PRIMARY_SCORE
    if secondary in scores:
        scores[secondary] = SECONDARY_SCORE
    return scores


def upgrade() -> None:
    conn = op.get_bind()

    # Kolom kanonis untuk nama role adalah `title` (lihat
    # `622dd9a82d43_add_catalog_and_roadmap_tables`). Versi awal migrasi ini
    # membaca kolom `name` yang hanya ada di database yang kolomnya ditambah
    # manual, sehingga `alembic upgrade head` di database kosong selalu gagal
    # di sini dengan `column "name" does not exist`.
    role_rows = conn.execute(sa.text("SELECT id, title, emoji FROM roles")).fetchall()
    roles = {r[0]: {"name": r[1], "emoji": r[2] or ""} for r in role_rows}
    if not roles:
        return
    all_roles = list(roles)

    for email, (primary, secondary) in DEMO_ROLE_FIXES.items():
        if primary not in roles:
            continue
        meta = roles[primary]
        conn.execute(
            sa.text(
                """
                UPDATE user_preferences up
                SET role_id = :role_id,
                    role_title = :role_title,
                    role_emoji = :role_emoji,
                    role_scores = CAST(:role_scores AS jsonb),
                    updated_at = now()
                FROM users u
                WHERE up.user_id = u.id AND u.email = :email
                """
            ),
            {
                "role_id": primary,
                "role_title": meta["name"],
                "role_emoji": meta["emoji"],
                "role_scores": json.dumps(_build_scores(all_roles, primary, secondary)),
                "email": email,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    # Kembalikan bentuk skor seed (satu kunci) dan kosongkan emoji.
    conn.execute(
        sa.text(
            """
            UPDATE user_preferences up
            SET role_scores = jsonb_build_object(up.role_id, 10),
                role_emoji = '',
                updated_at = now()
            FROM users u
            WHERE up.user_id = u.id
              AND u.email IN ('siti@sepaham.local', 'budi@sepaham.local',
                              'nadia@sepaham.local', 'rian@sepaham.local',
                              'salsa@sepaham.local', 'kevin@sepaham.local')
            """
        )
    )
    # Nadia & Kevin kembali ke role_id seed (frontend-engineer).
    conn.execute(
        sa.text(
            """
            UPDATE user_preferences up
            SET role_id = 'frontend-engineer',
                role_title = CASE u.email
                    WHEN 'nadia@sepaham.local' THEN 'UI/UX'
                    ELSE 'Fullstack'
                END,
                role_scores = jsonb_build_object('frontend-engineer', 10)
            FROM users u
            WHERE up.user_id = u.id
              AND u.email IN ('nadia@sepaham.local', 'kevin@sepaham.local')
            """
        )
    )
