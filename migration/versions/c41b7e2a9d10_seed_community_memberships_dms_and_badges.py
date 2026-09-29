"""seed_community_memberships_dms_and_badges

Revision ID: c41b7e2a9d10
Revises: 9eca0fe13df8
Create Date: 2026-09-27 12:40:00.000000

Perbaikan data seed yang membuat fitur Community/Chat kosong total:
  - `server_members` tidak pernah diisi, padahal 3 server + 8 channel + 5 pesan
    di-seed. Akibatnya `GET /api/community/mine` selalu `{"communities": []}`
    untuk semua user: tidak ada server, tidak ada channel, tidak ada pesan.
  - `direct_conversations` kosong, jadi daftar DM selalu kosong.
  - `user_badges` kosong, jadi kartu badge di profile selalu kosong.
  - `messages.author_id` NULL padahal `author_name` menunjuk user nyata, sehingga
    avatar & relasi penulis di chat kosong.

Server `ugm` sengaja dibiarkan tanpa anggota supaya alur "discover server lalu
join" tetap punya target yang belum di-join.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c41b7e2a9d10"
down_revision: Union[str, Sequence[str], None] = "9eca0fe13df8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ITB = "Institut Teknologi Bandung"


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. server_members -------------------------------------------------
    # Semua pengguna PTY/ITB ikut server ITB; Nadia (UI/UX) juga ikut server UI.
    conn.execute(
        sa.text(
            """
            INSERT INTO server_members (server_id, user_id, joined_at)
            SELECT 'itb', p.user_id, now()
            FROM profiles p
            WHERE p.university = :itb
            ON CONFLICT (server_id, user_id) DO NOTHING
            """
        ),
        {"itb": ITB},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO server_members (server_id, user_id, joined_at)
            SELECT 'ui', p.user_id, now()
            FROM profiles p
            JOIN users u ON u.id = p.user_id
            WHERE u.email = 'nadia@sepaham.local'
            ON CONFLICT (server_id, user_id) DO NOTHING
            """
        )
    )

    # --- 2. author_id untuk pesan yang tertanam ---------------------------
    conn.execute(
        sa.text(
            """
            UPDATE messages m
            SET author_id = u.id
            FROM users u
            WHERE m.author_id IS NULL
              AND lower(m.author_name) = lower(u.name)
            """
        )
    )

    # --- 3. direct_conversations + pesan DM --------------------------------
    # Satu row per pasangan (user_low < user_high) lalu pesan dari kedua pihak.
    dms = [
        ("siti@sepaham.local", "budi@sepaham.local", [
            ("Budi Santoso", "Siti, kerjain review page-nya udah mulai?"),
            ("Siti Rahma", "Sudah, tinggal bagian responsive mobile."),
            ("Budi Santoso", "Kalau butuh review API-nya bilang aja."),
        ]),
        ("siti@sepaham.local", "salsa@sepaham.local", [
            ("Salsabila", "Siti, data pipeline-nya sudah jalan belum?"),
            ("Siti Rahma", "Masih ETL-nya. Sore aku kabarin ya."),
        ]),
        ("budi@sepaham.local", "rian@sepaham.local", [
            ("Budi Santoso", "Rian, state management-nya pakai apa?"),
            ("Rian Hidayat", "Riverpod. Lumayan enak buat dapat scalability."),
        ]),
    ]

    for email_a, email_b, messages in dms:
        rows = conn.execute(
            sa.text("SELECT id, name, email FROM users WHERE email IN (:a, :b)"),
            {"a": email_a, "b": email_b},
        ).fetchall()
        by_email = {r[2]: (r[0], r[1]) for r in rows}
        if email_a not in by_email or email_b not in by_email:
            continue

        low, high = sorted([by_email[email_a][0], by_email[email_b][0]], key=str)
        id_by_name = {name: uid for uid, name in by_email.values()}

        existing = conn.execute(
            sa.text("SELECT id FROM direct_conversations WHERE user_low = :low AND user_high = :high"),
            {"low": low, "high": high},
        ).scalar()
        if existing:
            continue

        dm_id = conn.execute(
            sa.text(
                """
                INSERT INTO direct_conversations (id, user_low, user_high, created_at)
                VALUES (gen_random_uuid(), :low, :high, now())
                RETURNING id
                """
            ),
            {"low": low, "high": high},
        ).scalar()

        for author_name, body in messages:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO messages (
                        id, channel_id, dm_id, parent_id, author_id, author_name,
                        author_avatar, body, code_language, code_content,
                        attachment_name, attachment_kind, attachment_size,
                        anonymous, created_at
                    )
                    VALUES (
                        gen_random_uuid(), NULL, :dm_id, NULL, :author_id, :author_name,
                        '', :body, NULL, NULL, NULL, NULL, NULL, false, now()
                    )
                    """
                ),
                {
                    "dm_id": dm_id,
                    "author_id": id_by_name.get(author_name),
                    "author_name": author_name,
                    "body": body,
                },
            )

    # --- 4. user_badges ----------------------------------------------------
    # Badge diberikan sesuai aktivitas yang masuk akal dengan data seed.
    awards = [
        ("siti@sepaham.local", ["first-commit", "streak-7"]),
        ("budi@sepaham.local", ["first-commit", "streak-7", "contributor"]),
        ("salsa@sepaham.local", ["first-commit", "streak-7", "polyglot"]),
        ("rian@sepaham.local", ["first-commit", "night-owl"]),
        ("nadia@sepaham.local", ["first-commit", "rising-star"]),
        ("kevin@sepaham.local", ["first-commit"]),
    ]
    for email, badge_ids in awards:
        conn.execute(
            sa.text(
                """
                INSERT INTO user_badges (user_id, badge_id, earned, earned_at)
                SELECT u.id, b.id, true, now()
                FROM users u, badges b
                WHERE u.email = :email AND b.id = ANY(:badge_ids)
                ON CONFLICT (user_id, badge_id) DO NOTHING
                """
            ),
            {"email": email, "badge_ids": badge_ids},
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Hapus hanya baris yang dibuat migrasi ini (user seed, bukan user nyata).
    conn.execute(
        sa.text(
            """
            DELETE FROM server_members sm
            USING users u
            WHERE sm.user_id = u.id AND u.email LIKE '%%@sepaham.local'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM user_badges ub
            USING users u
            WHERE ub.user_id = u.id AND u.email LIKE '%%@sepaham.local'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM messages
            WHERE channel_id IS NULL
            """
        )
    )
    conn.execute(sa.text("DELETE FROM direct_conversations"))
    conn.execute(sa.text("UPDATE messages SET author_id = NULL WHERE author_id IS NOT NULL"))
