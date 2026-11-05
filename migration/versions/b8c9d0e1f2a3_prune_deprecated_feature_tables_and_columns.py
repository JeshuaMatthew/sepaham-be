"""prune_deprecated_feature_tables_and_columns

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-16 17:55:00.000000

Menghapus tabel dan kolom dari fitur-fitur yang telah dipangkas oleh dosen pembimbing:
- Ruang Komunitas & Chat: channels, messages, direct_conversations, servers, server_members, community_invites
- Kolaborasi: collab_requests, collab_applicants, collab_request_images
- Karir & Magang: ai_internships, internship_contacts
- Lencana & GitHub: badges, user_badges, github_repos, github_stats
- Media & Kutipan: dev_quotes, lofi_tracks
- Evaluasi & Pelacakan Aktivitas Roadmap: submissions, roadmap_activity
- Kolom deprecated pada roadmap_nodes: submission, missions
- Kolom deprecated pada profiles: cv_file_name, cv_uploaded_at, github_connected, github_username
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Hapus tabel-tabel fitur yang telah dikeluarkan (dengan CASCADE)
    tables_to_drop = [
        "messages",
        "channels",
        "direct_conversations",
        "community_invites",
        "server_members",
        "collab_applicants",
        "collab_request_images",
        "collab_requests",
        "servers",
        "user_badges",
        "badges",
        "github_repos",
        "github_stats",
        "internship_contacts",
        "ai_internships",
        "dev_quotes",
        "lofi_tracks",
        "submissions",
        "roadmap_activity",
    ]

    for table_name in tables_to_drop:
        bind.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))

    # 2. Hapus kolom-kolom deprecated pada tabel roadmap_nodes
    bind.execute(sa.text("ALTER TABLE roadmap_nodes DROP COLUMN IF EXISTS submission"))
    bind.execute(sa.text("ALTER TABLE roadmap_nodes DROP COLUMN IF EXISTS missions"))

    # 3. Hapus kolom-kolom deprecated pada tabel profiles
    bind.execute(sa.text("ALTER TABLE profiles DROP COLUMN IF EXISTS cv_file_name"))
    bind.execute(sa.text("ALTER TABLE profiles DROP COLUMN IF EXISTS cv_uploaded_at"))
    bind.execute(sa.text("ALTER TABLE profiles DROP COLUMN IF EXISTS github_connected"))
    bind.execute(sa.text("ALTER TABLE profiles DROP COLUMN IF EXISTS github_username"))


def downgrade() -> None:
    pass

